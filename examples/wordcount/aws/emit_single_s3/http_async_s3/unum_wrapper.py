from lambda_handler import lambda_handler as user_lambda
from enum import Enum
import json
import boto3
import uuid
import os
import time

class NodeType(Enum):
    oneToOne = 0
    manyToMany = 1
    manyToOne = 2
    oneToMany = 3
    end = 4


class Coordinator(object):

    def __init__(self, config):
        if config['type'] == "manyToMany":
            self.type = NodeType.manyToMany
            self.invokee = config['next']
            self.invokeeReturnStore = config['invokeeReturnStore']
        elif config['type'] == "manyToOne":
            self.type = NodeType.manyToOne
            self.invokee = config['next']
        elif config['type'] == "oneToOne":
            self.type = NodeType.oneToOne
            self.invokee = config['next']
        elif config['type'] == "oneToMany":
            self.type = NodeType.oneToMany
            self.invokee = config['next']
        elif config['type'] == "end":
            self.type = NodeType.end
        else:
            raise IOError(f'unknown node type')

        self.lambda_client = boto3.client('lambda')

    def httpAsyncInvoke(self, data):
        # data should be JSON serializable
        response = self.lambda_client.invoke(
        FunctionName=self.invokee,
        InvocationType='Event',
        LogType='None',
        Payload=json.dumps(data),
        )

        return response

def ingress(event, context, myCoordinator):

    if 'unum_metadata' not in event:
        myCoordinator.myInput = event['data']
        return

    unum_metadata = event['unum_metadata']

    if myCoordinator.type == NodeType.manyToOne:
        myCoordinator.fan = {'size': unum_metadata['fanOutSize'], 'myIndex': unum_metadata['index']}
        myCoordinator.returnValueStore = unum_metadata['returnValueStore']
        myCoordinator.myInput = event['data']

    if myCoordinator.type == NodeType.manyToMany or myCoordinator.type == NodeType.end:
        if unum_metadata["inputType"] == "s3":
            data = event['data']
            s3_client = boto3.client('s3')

            response = s3_client.list_objects(
                Bucket=data['bucket'],
                Prefix=f"{data['directory']}/" # e.g., reducer0/
            )

            keys = [e['Key'] for e in response['Contents']]
            
            myInput = []

            
            os.makedirs(f"/tmp/{data['directory']}")
            # if not os.path.exists(f"/tmp/{data['directory']}"):
            #     raise IOError(f"directory /tmp/{data['directory']} does not exist")

            # raise IOError(f'{keys}')

            for k in keys:
                if k.endswith('/'):
                    continue

                s3_client.download_file(data['bucket'], k, f"/tmp/{k}")
                with open(f"/tmp/{k}", 'r') as f:
                    d = f.read()
                    myInput.append(json.loads(d))

            myCoordinator.myInput = myInput

        else:
            raise IOError(f'Unknown input type: {unum_metadata["inputType"]}')
    

def egress(output, context, myCoordinator):

    if myCoordinator.type == NodeType.manyToMany:
        # check if the user function output is an array
        if isinstance(output, list) == False:
            raise IOError(f'Many-to-many node requires list output but instead got {type(output)}. {output}')

        myCoordinator.nextInput = output
        myCoordinator.nextInputLen = len(output)

        # allocate data store for invokees' return values
        if myCoordinator.invokeeReturnStore['type'] == 's3':
            # create a unique directory
            s3_client = boto3.client('s3')

            directoryName = f'{uuid.uuid4()}'
            s3_client.put_object(Bucket=myCoordinator.invokeeReturnStore['bucket'], Key=(directoryName+'/'))
            myCoordinator.invokeeReturnStore['directory'] = directoryName

        elif myCoordinator.invokeeReturnStore['type'] == 'dynamodb':
            pass
        elif myCoordinator.invokeeReturnStore['type'] == 'redis':
            pass
        elif myCoordinator.invokeeReturnStore['type'] == 'elasticache':
            pass
        else:
            raise IOError(f'Unknown data store for invokee return values')

        nextInput = []

        for i, d in enumerate(myCoordinator.nextInput):
            p = {}
            p['data'] = d
            p['unum_metadata'] = {'returnValueStore': myCoordinator.invokeeReturnStore,
                                  'index':i,
                                  'fanOutSize': myCoordinator.nextInputLen}

            nextInput.append(p)

        myCoordinator.nextInput = nextInput

        rsp = []
        for d in myCoordinator.nextInput:
            rsp.append(myCoordinator.httpAsyncInvoke(d))

        for r in rsp:
            r['Payload'].read()

    elif myCoordinator.type == NodeType.manyToOne:
        # First write my return values to the datastore in
        # myCoordinator.returnValueStore. Then if I'm the last invokee in the
        # fan, wait until all the other invokees write to the
        # returnValueStore, then invoke the next stage and pass to it the
        # datastore pointer.
        if myCoordinator.returnValueStore['type'] == 's3':
            s3_client = boto3.client('s3')

            fn = f"index-{myCoordinator.fan['myIndex']}-outof-{myCoordinator.fan['size']}.json"
            local_file_path = '/tmp/'+fn

            with open(local_file_path, 'w') as f:
                f.write(json.dumps(output))

            s3_client.upload_file(local_file_path, myCoordinator.returnValueStore['bucket'], f"{myCoordinator.returnValueStore['directory']}/{fn}")

            if myCoordinator.fan['myIndex']+1 == myCoordinator.fan['size']:
                # wait until all other invokees complete
                keys = []
                while len(keys) < myCoordinator.fan['size']:
                    response = s3_client.list_objects(
                        Bucket=myCoordinator.returnValueStore['bucket'],
                        Prefix=f"{myCoordinator.returnValueStore['directory']}/" # e.g., reducer0/
                    )

                    keys = list(filter(lambda x: x.endswith('/') == False, [e['Key'] for e in response['Contents']]))

                    if len(keys) == myCoordinator.fan['size']:
                        break
                    elif len(keys) > myCoordinator.fan['size']:
                        raise IOError(f'More invokee return values than fan-out size')

                    time.sleep(0.1)

                dataInS3 = {
                    "unum_metadata": {"inputType":"s3", "fanOutSize": myCoordinator.fan['size']},
                    "data": {"bucket": myCoordinator.returnValueStore['bucket'], "directory": myCoordinator.returnValueStore['directory']}
                }
                rsp = myCoordinator.httpAsyncInvoke(dataInS3)
                rsp['Payload'].read()

        else:
            raise IOError(f"Unknown data store type for manyToOne returnValueStore: {myCoordinator.returnValueStore['type']}")

    elif myCoordinator.type == NodeType.end:
        # raise IOError(f'{output}')
        pass

    else:
        raise IOError(f'Unknown Coordinator type: {myCoordinator.type}')


def lambda_handler(event, context):
    with open('unum_config.json', 'r') as f:
        c = f.read()
        config = json.loads(c)

    myCoordinator = Coordinator(config)

    ingress(event, context, myCoordinator)

    user_function_output = user_lambda(myCoordinator.myInput, context)

    egress(user_function_output, context, myCoordinator)

    return user_function_output
    
