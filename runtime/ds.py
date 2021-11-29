import boto3
import uuid
import time, datetime, json, os, math

from botocore.exceptions import ClientError

class UnumIntermediaryDataStore(object):
    
    subclasses = {}

    def __init__(self, ds_type, ds_name, debug):
        '''
            @param type s3|dynamodb|redis|elasticache|fs|efs
            @param name s3 bucket | dynamodb table
        '''
        self.my_type = ds_type
        self.name = ds_name
        self.debug = debug


    @classmethod
    def add_datastore(cls, datastore_type):
        def wrapper(subclass):
            cls.subclasses[datastore_type] = subclass
            return subclass

        return wrapper


    @classmethod
    def create(cls, datastore_type, *params):
        if datastore_type not in cls.subclasses:
            raise ValueError(f'unum does not support {platform} as intermediary data store')

        return cls.subclasses[datastore_type](*params)


@UnumIntermediaryDataStore.add_datastore('dynamodb')
class DynamoDBDriver(UnumIntermediaryDataStore):


    def __init__(self, ds_name, debug):
        super(DynamoDBDriver, self).__init__("dynamodb", ds_name, debug)
        self.client = boto3.client('dynamodb')
        self.resource = boto3.resource('dynamodb')
        self.table = self.resource.Table(self.name)


    def read_input(self, session, values):
        '''Given the workflow invocation session id and a list of pointers to
        the intermediary data store, read all data and return them as an
        ordered list.

        Data in the returned list should correspond to the pointers in the
        `values` parameter *in the same order*.

        In practice, this function is only used by fan-in functions to read
        its inputs which are the outputs of all fan-out functions.

        Each element in the `values` list are *instance names*.

        The pointers are used as is. It is the invoker's responsibility to
        expand the pointers and make sure that they are valid. unum no longer
        uses glob patterns in the the runtime payload (but the unum config
        language still supports glob patterns) and the invoker should expand
        all glob patterns to concrete data pointer names.

        unum's fan-in semantics requires that the fan-in function be invoked
        only when ALL its inputs are available. Therefore, if one of the
        pointers in the `values` list doesn't exist in the data store, this
        function will throw an exception.

        On AWS, there's no reason to pass in a single data pointer when
        invoking a Lambda because asynchronous HTTP requests achieves the same
        results by adding the data onto Lambda's event queue. Therefore, the
        `values` parameter should always be a list. We don't consider the
        scenario where `values` is a dict.
        '''
        item_names = [f'{session}/{v}-output' for v in values]
        request_keys = [{'Name': k} for k in item_names]

        '''
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.ServiceResource.batch_get_item
        A example response of batch_get_item():

            {
                'Responses': {
                    'unum-dynamo-test-table': [
                        {
                            'Value': 'Hardcoded client put_item()',
                            'Name': '2c48bf10-fecf-4832-b25a-db1d4b9df840/Client-output'
                        },
                        {
                            'Value': 'Hardcoded Table put_item()',
                            'Name': '2c48bf10-fecf-4832-b25a-db1d4b9df840/Table-output'
                        }
                    ]
                },
                'UnprocessedKeys': {},
                'ResponseMetadata': {
                    'RequestId': 'UNE6VCORLFIED1LISTBG0M6VNJVV4KQNSO5AEMVJF66Q9ASUAAJG',
                    'HTTPStatusCode': 200,
                    'HTTPHeaders': {
                        'server': 'Server',
                        'date': 'Sun, 03 Oct 2021 02:15:41 GMT',
                        'content-type': 'application/x-amz-json-1.0',
                        'content-length': '285',
                        'connection': 'keep-alive',
                        'x-amzn-requestid': 'UNE6VCORLFIED1LISTBG0M6VNJVV4KQNSO5AEMVJF66Q9ASUAAJG',
                        'x-amz-crc32': '4084553720'
                    },
                    'RetryAttempts': 0
                }
            }

        NOTE: dynamodb.resource.batch_get_item() does NOT tell you which
        requested item it didn't find in the table.

        NOTE: If you request more than 100 items, BatchGetItem returns a
        ValidationException with the message "Too many items requested for the
        BatchGetItem call."

        NOTE: A single operation can retrieve up to 16 MB of data.
        BatchGetItem returns a partial result if the response size limit is
        exceeded. If a partial result is returned, the operation returns a
        value for UnprocessedKeys. You can use this value to retry the
        operation starting with the next item to get.

        NOTE: BatchGetItem returns a partial result if the table's provisioned
        throughput is exceeded, or an internal processing failure occurs. If a
        partial result is returned, the operation returns a value for
        UnprocessedKeys . You can use this value to retry the operation
        starting with the next item to get.

        If none of the items can be processed due to insufficient provisioned
        throughput on all of the tables in the request, then BatchGetItem
        returns a ProvisionedThroughputExceededException . If at least one of
        the items is successfully processed, then BatchGetItem completes
        successfully, while returning the keys of the unread items in
        UnprocessedKeys .
        '''

        all_ret = []

        for i in range(math.ceil(len(request_keys)/100)):
            this_batch = request_keys[i*100:(i+1)*100]

            this_batch_items = self.resource.batch_get_item(
                RequestItems={
                    self.name: {
                        'Keys': this_batch,
                        'ProjectionExpression': '#Name, #Value',
                        'ExpressionAttributeNames': {
                            '#Name': 'Name',
                            '#Value': 'Value'
                        },
                        'ConsistentRead': True,
                    }
                })

            try:
                ret = this_batch_items['Responses'][self.name]
                all_ret = all_ret+ret

            except KeyError as e:
                print(this_batch_items)
                raise e

        # return a sorted array by the originally requested order
        order = {n: i for i, n in enumerate(item_names)}

        vals = [json.loads(e['Value']) for e in sorted(all_ret, key=lambda d: order[d['Name']])]

        if len(vals) < len(values):
            print(f'[WARN] Not all values for fan-in were read from {self.my_type}')
            print(f'[WARN] Expect {len(values)}. Got {len(vals)}')
            print(all_ret)
        elif len(vals) > len(values):
            print(f'[WARN] More fan-in values read from {self.my_type} than expanded')

        return vals



    def get_checkpoint(self, session, instance_name):
        '''Given the session ID and the function's instance name, return the
        checkpoint's contents or None if the checkpoint doesn't exist.

        This function uses DynamoDB's GetItem API and request to read the
        `Value` field from the item.

        There doesn't seem to be a faster API to only check whether an item
        exists in DynamoDB without getting some of its attributes. GetItem
        seems to be the only API for this purpose.

        The GetItem operation returns the attributes requested in the
        ProjectionExpression for the item with the given primary key. If there
        is no matching item, GetItem does not return any data and there will
        be no Item element in the response.

        Example response:

        ```
        {
            'Item': {
                'string': 'string'|123|Binary(b'bytes')|True|None|set(['string'])|set([123])|set([Binary(b'bytes')])|[]|{}
            }
        }
        ```

        @session str
        @instance_name str
        '''
        try:
            ret = self.table.get_item(
                Key={
                    'Name': self.get_checkpoint_name(session, instance_name)
                },
                ConsistentRead=True,
                ProjectionExpression='#Value',
                ExpressionAttributeNames= {
                    '#Value': 'Value'
                })
        except Exception as e:
            print(f"[WARN] get_checkpoint() Error Code: {e.response['Error']['Code']}")
            raise e

        if "Item" in ret:
            return ret["Item"]["Value"]
        else:
            return None



    def get_checkpoint_name(self, session, instance_name):
        '''Given the session ID and instance name, return the name of its
        DynamoDB checkpoint
        '''
        return f'{session}/{instance_name}-output'



    def checkpoint(self, session, instance_name, user_function_output):
        '''Writing the user function output as an item with a unique name

        This function creates a single item in the dynamoDB table. The item
        contains the user function output of this particular function
        instance.

        Items have the following schema:

        ```
        {
            "Session": "a uuid4 string",
            "Name": "<session>/<instance_name>-output",
            "Value": "function result as a JSON string"
        }
        ```

        The "Name" field is the primary key.

        The "Value" field is of type string and is
        json.dumps(user_function_output)

        This function will only try to write if an item with the same "Name"
        does NOT already exists. If an item with the same "Name" already
        exists, the DynamoDB PutItem call is called and this function returns
        1.

        If the data to write failed DynamoDB's schema validation, return 2.
        '''
        try:

            self.table.put_item(Item={
                    "Session": session,
                    "Name": self.get_checkpoint_name(session, instance_name),
                    "Value": json.dumps(user_function_output)
                },
                ConditionExpression='attribute_not_exists(#N)',
                ExpressionAttributeNames={"#N": "Name"}

            )

            # if self.debug:
            #     ret = self.table.put_item(Item={
            #             "Session": session,
            #             "Name": self.get_checkpoint_name(session, instance_name),
            #             "Value": json.dumps(user_function_output)
            #         },
            #         ConditionExpression='attribute_not_exists(#N)',
            #         ExpressionAttributeNames={"#N": "Name"},
            #         ReturnConsumedCapacity="TOTAL"
            #     )
            #     print(f"[ds.dynamodb.checkpoint] put_item consumed capacity: {ret['ConsumedCapacity']['CapacityUnits']}")
            # else:
            #     self.table.put_item(Item={
            #             "Session": session,
            #             "Name": self.get_checkpoint_name(session, instance_name),
            #             "Value": json.dumps(user_function_output)
            #         },
            #         ConditionExpression='attribute_not_exists(#N)',
            #         ExpressionAttributeNames={"#N": "Name"}

            #     )

            return 0
        except ClientError as e:  
            if e.response['Error']['Code']=='ConditionalCheckFailedException':  
                return 1
            elif e.response['Error']['Code']=='ValidationException':
                raise e
            else:
                raise e
        except Exception as e:
            print(f"[WARN] Error Code is {e.response['Error']['Code']}")
            raise e



    def _update_fan_in_counter(self, session, counter_name):
        '''Given the session and counter name, create the counter with initial
        0 if it does not already exist. Or increments the counter by 1
        atomically. Return the counter value after update.

        According to
        https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.AtomicCounters,
        UpdateItem with SET on numerical values are guaranteed to be atomic.
        '''
        try:
            ret = self.table.put_item(Item={
                    "Name": f'{session}/{counter_name}',
                    "Count": 0
                },
                ConditionExpression='attribute_not_exists(#N)',
                ExpressionAttributeNames={"#N": "Name"}

            )
        except ClientError as e:  
            if e.response['Error']['Code']=='ConditionalCheckFailedException':  
                pass
            else:
                raise e
        except Exception as e:
            raise e


        try:
            ret = self.table.update_item(
                Key={"Name": f'{session}/{counter_name}'},
                ReturnValues='UPDATED_NEW',
                UpdateExpression='SET #C = #C + :incr',
                ConditionExpression='attribute_exists(#N)',
                # ExpressionAttributeNames={
                #     'string': 'string'
                # },
                ExpressionAttributeValues={':incr': 1},
                ExpressionAttributeNames={"#N": "Name", "#C": 'Count'})
        except Exception as e:
            raise e

        return ret["Attributes"]["Count"]


    def _update_fan_in_counter_array(self, session, counter_name, my_index, array_size):
        '''Given the session and counter name, create the counter with initial
        0 if it does not already exist. Or increments the counter by 1
        atomically. Return the counter value after update.
        '''
        bitmap = [False for i in range(array_size)]
        try:
            ret = self.table.put_item(Item={
                    "Name": f'{session}/{counter_name}',
                    "ReadyMap": bitmap
                },
                ConditionExpression='attribute_not_exists(#N)',
                ExpressionAttributeNames={"#N": "Name"}

            )
        except ClientError as e:  
            if e.response['Error']['Code']=='ConditionalCheckFailedException':  
                pass
            else:
                raise e
        except Exception as e:
            raise e

        try:
            ret = self.table.update_item(
                Key={"Name": f'{session}/{counter_name}'},
                ReturnValues='UPDATED_NEW',
                UpdateExpression='SET ReadyMap = #C + :incr',
                ConditionExpression='attribute_exists(#N)',
                # ExpressionAttributeNames={
                #     'string': 'string'
                # },
                ExpressionAttributeValues={':incr': 1},
                ExpressionAttributeNames={"#N": "Name"})
        except Exception as e:
            raise e

        return ret["Attributes"]["ReadyMap"]

    def check_fan_in_complete(self, session, values, target_count):
        '''Increment the counter and check if fan-in is complete

        Fan-in with DynamoDB is considered complete when the counter number
        equals the fan-out size.
        '''
        counter_name = ""
        for v in values:
            counter_name = f'{counter_name}{v}-'
        counter_name = f'{counter_name}counter'

        ret = self._update_fan_in_counter(session, counter_name)

        return ret == target_count

        # ret = self._update_fan_in_counter_array(session, counter_name, fan_out_size)

        # count = 0
        # for b in ret:
        #     if b:
        #         count = count+1

        # return count == target_count


class S3Driver(UnumIntermediaryDataStore):
    def __init__(self, ds_name):
        ''' Initialze an s3 data store

        Raise an exception if the bucket doesn't exist.

        @ param ds_name an s3 bucket name
        '''
        super(S3Driver, self).__init__("s3", ds_name)
        self.backend = boto3.client("s3")
        # check if this bucket exists and this function has permission to
        # access it
        try:
            response = self.backend.head_bucket(Bucket=self.name)
        except:
            raise IOError(f'The intermediary s3 bucket does NOT exist')


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

    def read_input(self, session, values):
        '''Given the workflow invocation session id and a list of pointers to
        the intermediary data store, read all data and return them as an
        ordered list.

        Data in the returned list should correspond to the pointers in the
        `values` parameter _in the same order_.

        In practice, this function is used by the fan-in function to read its
        input, which is the outputs of all fan-out functions, from the
        intermediary data store.

        Each element in the `values` list combined with `session` (e.g.,
        "{session}/{values[0]}-output.json") is a key in the intermediary s3
        bucket.

        The pointers are used as is. It is the invoker's responsibility to
        expand the pointers and make sure that they are valid. unum no longer
        uses glob patterns in the the runtime payload (but the unum config
        language still supports glob patterns) and the invoker should expand
        all glob patterns to concrete data pointer names.

        unum guarantees that all pointers in `values` exists when this
        function is called (i.e., when the fan-in function is invoked).
        Therefore, if one of the pointers doesn't exist in the data store,
        this function will throw an exception.

        On AWS, there's no reason to pass in a single data pointer when
        invoking a Lambda because asynchronou HTTP requests achieves the same
        results by adding the data onto Lambda's event queue. Therefore, the
        `values` parameter should always be a list. We don't consider the
        scenario where `values` is a dict.
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


