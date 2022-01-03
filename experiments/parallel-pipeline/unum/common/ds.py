import boto3
import uuid
import time, datetime, json, os

class ReturnValueStoreDriver(object):
    def __init__(self, ds_type, ds_name):
        '''
            @param type s3|dynamodb|redis|elasticache|fs|efs
            @param name s3 bucket | dynamodb table
        '''
        self.my_type = ds_type
        self.name = ds_name
        self.backend = None

class S3Driver(ReturnValueStoreDriver):
    def __init__(self, ds_name):
        ''' Initialze an s3 data store

        Raise an exception if the bucket doesn't exist.

        @ param ds_name an s3 bucket name
        '''
        super(S3Driver, self).__init__("s3", ds_name)
        self.backend = boto3.client("s3")
        # check if this bucket exists and this function has permission to
        # access it
        response = self.backend.head_bucket(Bucket=self.name)


    def create_session(self):
        ''' Create a prefix (directory) in the bucket
        '''
        return f'{uuid.uuid4()}'

    def create_fanin_context(self):
        ''' For the fan-out functions to write their outputs, creates a s3
        directory
        DEPRECATED
        '''
        directoryName = f'{uuid.uuid4()}'
        self.backend.put_object(Bucket=self.name, Key=(directoryName+'/'))

        return directoryName

    def read_input(self, session, ptr):
        ''' Given the pointer(s) in event["Data"]["Value"], read the value(s)
        from data store.

        The pointers are used as is. It is the invoker's the responsibility to
        make sure that the pointers are valid.

        If any of the pointers don't exist in the bucket, this function will
        keep retrying.

        '''
        s3_names = [f'{session}/{p}-output.json' for p in ptr]

        data = []

        for s3_name, p in zip(s3_names, ptr):
            local_file_name = f'{p}-output.json'
            self.backend.download_file(self.name, s3_name, f'/tmp/{local_file_name}')

            with open(f'/tmp/{local_file_name}', 'r') as f:
                data.append(json.loads(f.read()))

        return data

    def check_value_exist(self, session, name):
        pass


    def check_values_exist(self, session, names):

        s3_names = [f'{session}/{n}-output.json' for n in names]

        response = self.backend.list_objects_v2(
                        Bucket=self.name,
                        Prefix=f'{session}/' # e.g., reducer0/
                    )
        all_keys = [e["Key"] for e in response["Contents"]]

        for n in s3_names:
            if n not in all_keys:
                return False

        return True


    def write_error(self, session, name, msg):
        ''' Save an error message
        @session
        @name str name of the s3 file
        @msg json-serializable

        '''
        local_file_path = f'/tmp/{name}'
        with open(local_file_path, 'w') as f:
            f.write(json.dumps(msg))

        self.backend.upload_file(local_file_path,
                                 self.name,
                                 f'{session}/{name}')

    def write_return_value(self, session, ret_name, ret):
        ''' Write a user function's return value to the s3 bucket

        @param session a s3 prefix that is the session context
        @param ret_name the s3 file name
        @param ret the user function's return value
        '''
        fn = f'{ret_name}-output.json'
        local_file_path = '/tmp/'+fn
        with open(local_file_path, 'w') as f:
            f.write(json.dumps(ret))

        self.backend.upload_file(local_file_path,
                                 self.name,
                                 f'{session}/{fn}')

    def write_fanin_context(self, output, fcn_name, context, index, size):
        ''' Fan-out function writes its outputs to the fan-in s3 directory

            @param output function output
            @param fcn_name lambda function's name
            @param context s3 directory name (without the /)
            @param index function's index in the fan-out
            @param size fan-out size
            DEPRECATED
        '''
        fn = f"{fcn_name}-UINDEX-{index}-outof-{size}.json"
        local_file_path = '/tmp/'+fn

        with open(local_file_path, 'w') as f:
            f.write(json.dumps(output))

        self.backend.upload_file(local_file_path,
                                 self.name,
                                 f'{context}/{fn}')

    def get_index(self, fn):
        s = fn.split("UINDEX")[1]
        return s.split("-")[1]

    def check_prefix_index_exist(self, context, prefix, index):
        file_list = self.list_fanin_context(context)
        file_list = [e.replace(f'{context}/',""), file_list]
        target_list = list(filter(lambda x : x.startswith(prefix), l))
        for p in target_list:
            if self.get_index(p) == index:
                return True

        return False

    def list_fanin_context(self, context):
        ''' List all the files in the s3 fan-in directory
        '''
        response = self.backend.list_objects(
                        Bucket=self.name,
                        Prefix=f'{context}/' # e.g., reducer0/
                    )

        keys = list(filter(lambda x: x.endswith('/') == False, [e['Key'] for e in response['Contents']]))

        return keys

    def read_fanin_context(self, context, keys=None):
        ''' Read all files in the fan-in directory and return it as an ordered
        list
        '''
        response = self.backend.list_objects(
            Bucket=self.name,
            Prefix=f"{context}/" # e.g., reducer0/
            )

        file_list = [e['Key'] for e in response['Contents']]
           
        os.makedirs(f"/tmp/{context}", exist_ok = True)

        if keys != None:
            file_list = filter(lambda x : x in keys, file_list)

        for k in file_list:
            if k.endswith('/'):
                continue

            self.backend.download_file(self.name, k, f"/tmp/{k}")

        # return data as a list
        ret = []
        fl = os.listdir(f"/tmp/{context}/")
        fnc = fl[0].split('UINDEX')
        prefix = f'{fnc[0]}UINDEX'
        tmp = fnc[1].split('-')
        suffix = f'{tmp[2]}-{tmp[3]}'

        for i in range(len(fl)):

            with open(f'/tmp/{context}/{prefix}-{i}-{suffix}', 'r') as f:
                ret.append(json.loads(f.read()))

        return ret

class DynamoDBDriver(ReturnValueStoreDriver):
    def __init__(self, ds_name):
        super(DynamoDBDriver, self).__init__("dynamodb", ds_name)
        self.backend = boto3.client("dynamodb")

    def create_session(self):
        ''' Create a prefix (directory) in the bucket
        '''
        pass
