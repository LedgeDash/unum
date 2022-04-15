import uuid
import time, datetime, json, os, math


if os.environ['FAAS_PLATFORM'] == 'aws':
    import boto3
    from botocore.exceptions import ClientError
elif os.environ['FAAS_PLATFORM'] =='gcloud':
    from google.cloud import firestore
    from google.cloud import exceptions as gcloudexceptions

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



@UnumIntermediaryDataStore.add_datastore('firestore')
class FirestoreDriver(UnumIntermediaryDataStore):
    '''
    In the gcloud Firestore implementation, each session is saved in its own
    collection. The collection name is the session id. Checkpoints are
    documents in the collection with the function's instance name as its
    document name.
    '''
    def __init__(self, ds_name, debug):
        super(FirestoreDriver, self).__init__("firestore", ds_name, debug)
        self.db = firestore.Client()



    def _read(self, collection, document):
        doc_ref = self.db.collection(u'{}'.format(collection)).document(u'{}'.format(document))

        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            return None



    def read_input(self, collection, documents):
        '''Read multiple documents from a collection

        Used by the aggregation function to read its inputs
        '''

        print(f'Reading inputs from collection: {collection}, and documents: {documents}')
        
        return [self._read(collection, d) for d in documents]



    def get_checkpoint(self, session, instance_name):
        
        return self._read(session, instance_name)



    def _create_if_not_exist(self, collection, document, value):
        '''

        According to
        https://googleapis.dev/python/firestore/latest/document.html#google.cloud.firestore_v1.document.DocumentReference.create,
        create() will fail with google.cloud.exceptions.Conflict if the
        document already exists.

        It's not fully clear whether create if strongly consistent in that if
        I have 2 concurrent threads calling create, does it guarantee that one
        of the create() calls will fail with google.cloud.exceptions.Conflict?
        '''

        doc_ref = self.db.collection(u'{}'.format(collection)).document(u'{}'.format(document))

        try:
            doc_ref.create(value)

            return 1
        except gcloudexceptions.Conflict as e:
            return -1
        except Exception as e:
            print(f'[ERROR] Checkpointing encountered unexpected error: {e}')
            return -2


    def checkpoint(self, session, instance_name, data):
        '''

        @return 1 if successful. -1 if a checkpoint already exists. -2 if
            other errors.
        '''

        return self._create_if_not_exist(session, instance_name, data)



    def _delete(self, collection, document):
        '''Delete a document in a collection
        '''
        doc_ref = self.db.collection(u'{}'.format(collection)).document(u'{}'.format(document))

        try:
            doc_ref.delete()
            return 1

        except ClientError as e:
            raise e



    def delete_checkpoint(self, session, instance_name):
        return self._delete(session, instance_name)



    def gc_sync_point_name(self, session, parent_function_instance_name):

        return session, f'{parent_function_instance_name}-gc'



    def fanin_sync_point_name(self, session, aggregation_function_instance_name):

        return session, f'{aggregation_function_instance_name}-fanin'



    def gc_sync_ready(self, session, parent_function_instance_name, index, num_branches):
        '''Mark my gc as ready and check if gc is ready to run

        In the case of a parent node invoking multiple downstream child nodes,
        all child nodes need to have created their checkpoints before the
        parent node's checkpoint can be garbage collected. Unum have all child
        nodes synchronize via the intermediate datastore so that the
        last-to-finish child node deletes the parent's checkpoint.

        The synchronization item is named after the parent function's instance
        name. In practice, in Firestore, the collection name is the session id
        and the document name is the parent function's instance name with a
        "-gc" suffix.

        @return True is I'm the last-to-finish child node. False if I'm not.
        '''

        return self._sync_ready(self.gc_sync_point_name(session, parent_function_instance_name), index, num_branches)



    def fanin_sync_ready(self, session, aggregation_function_instance_name, index, num_branches):
        '''Mark my branch as ready and check if fan-in is ready to run

        In the case of fan-in, all upstream branches need to have created
        their checkpoints before the aggregation function is invoked. Unum
        have all branches synchronize via the intermediate datastore so that only
        the last-to-finish branch invokes the aggregation function.

        The synchronization item is named after the aggregation function's instance
        name. In practice, in Firestore, the collection name is the session id
        and the document name is the aggregation function's instance name with a
        "-fanin" suffix.

        @return True is I'm the last-to-finish branch. False if I'm not.
        '''

        return self._sync_ready(self.fanin_sync_point_name(session, aggregation_function_instance_name), index, num_branches)



    def _sync_ready(self, sync_point_name, index, num_branches):
        '''Mark the caller ready and return whether all branches are ready.

        @param sync_point_name tuple of session ID (as the Firestore
            collection name) and the synchronization object name (as the
            Firestore document name)
        @param index caller's index in the synchronization object
        @param num_branches the number of nodes that need to synchronize
        '''
        return self._sync_ready_bitmap(sync_point_name, index, num_branches)



    def _sync_ready_bitmap(self, sync_point_name, index, num_branches):
        self._create_bitmap(sync_point_name, num_branches)
        ready_map = self._update_bitmap_result(sync_point_name, index)

        return self._bitmap_ready(ready_map)



    def _create_bitmap(self, bitmap_name, bitmap_size):
        '''

        @param bitmap_name tuple
        '''
        collection = bitmap_name[0]
        document = bitmap_name[1]

        print(f'creating collection: {collection} and document: {document} as bitmap of length {bitmap_size}')

        value = {"ReadyMap": [False for i in range(bitmap_size)]}

        return self._create_if_not_exist(collection, document, value)



    def _update_bitmap_result(self, bitmap_name, index):

        # The default max retry attempts for Firestore transaction is only 5.
        # It is too low for fan-outs and I start to see transactions fail
        # around 15 parallel branches.
        transaction = self.db.transaction(max_attempts=500)
        bitmap_ref = self.db.collection(bitmap_name[0]).document(bitmap_name[1])

        @firestore.transactional
        def _update_my_index(transaction, bitmap_ref):
            snapshot = bitmap_ref.get(transaction=transaction)
            ready_map = snapshot.get('ReadyMap')

            # print(f'ReadyMap in snapshot: {ready_map}')

            ready_map[index] = True
            transaction.update(bitmap_ref, {
                'ReadyMap': ready_map
            })


            return ready_map

        try:
            result = _update_my_index(transaction, bitmap_ref)
        except Exception as e:
            # If the prior transaction failed, retry after a second
            result = _update_my_index(transaction, bitmap_ref)
            return result
        else:
            return result



    def _bitmap_ready(self, bitmap):
        '''Check if the bitmap is all True
        '''
        for b in bitmap:
            if b == False:
                return False
        return True



    def test(self):

        print(f'Firestore test')
        doc_ref = self.db.collection(u'users').document(u'alovelace')
        doc_ref.set({
            u'first': u'Ada',
            u'last': u'Lovelace',
            u'born': 1815
        })

        doc_ref = self.db.collection(u'users').document(u'aturing')
        doc_ref.set({
            u'first': u'Alan',
            u'middle': u'Mathison',
            u'last': u'Turing',
            u'born': 1912
        })

        users_ref = self.db.collection(u'users')
        docs = users_ref.stream()

        for doc in docs:
            print(f'{doc.id} => {doc.to_dict()}')

        session = f'{uuid.uuid4()}'

        self.checkpoint(session, 'test-function', {"output":"foo"})
        self.checkpoint(session, 'test-function', {"output":"foo"})




@UnumIntermediaryDataStore.add_datastore('dynamodb')
class DynamoDBDriver(UnumIntermediaryDataStore):


    def __init__(self, ds_name, debug):
        super(DynamoDBDriver, self).__init__("dynamodb", ds_name, debug)
        self.client = boto3.client('dynamodb')
        self.resource = boto3.resource('dynamodb')
        self.table = self.resource.Table(self.name)


    def read_input(self, session, values):
        '''Given the session id and a list of pointers to the intermediary
        data store, read all data and return them as an ordered list.

        Data in the returned list should correspond to the pointers in the
        `values` parameter *in the same order*.

        In practice, this function is only used by aggregation functions
        (fan-ins) to read its inputs.

        Elements in the `values` list are *instance names*.

        The pointers are used as is. It is the invoker's responsibility to
        expand the pointers and make sure that they are valid.
        Correspondingly, the IR of the fan-in branches, specifically the
        `Values` field that lists all fan-in branches, are written from the
        perspective of the branches (i.e., invokers).

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
                    'Name': self.checkpoint_name(session, instance_name)
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



    def _create_if_not_exist(self, key_name, key, value):
        '''Create an item in the DynamoDB table with primary key `key` and
        content `value` if the key does not already exist

        @return a positive integer if success. -1 if the key already exists.
        '''
        item = {key_name: key, **value}
        try:
            if self.debug:
                rsp = self.table.put_item(Item=item,
                    ConditionExpression='attribute_not_exists(#N)',
                    ExpressionAttributeNames={"#N": key_name},
                    ReturnConsumedCapacity='TOTAL'
                )

                return int(rsp['ConsumedCapacity']['CapacityUnits'])

            else:
                self.table.put_item(Item=item,
                    ConditionExpression='attribute_not_exists(#N)',
                    ExpressionAttributeNames={"#N": key_name}

                )
                return 1

        except ClientError as e:
            if e.response['Error']['Code']=='ConditionalCheckFailedException':
                return -1
            elif e.response['Error']['Code']=='ValidationException':
                raise e
            else:
                raise e
        except Exception as e:
            print(f"[WARN] Error Code is {e.response['Error']['Code']}")
            raise e



    def checkpoint_name(self, session, instance_name):
        '''Given the session ID and instance name, return the name of its
        DynamoDB checkpoint
        '''
        return f'{session}/{instance_name}-output'



    def checkpoint(self, session, instance_name, data):
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
        json.dumps(data)

        This function will only try to write if an item with the same "Name"
        does NOT already exists. If an item with the same "Name" already
        exists, the DynamoDB PutItem call is called and this function returns
        1.

        If the data to write failed DynamoDB's schema validation, return 2.
        '''

        return self._create_if_not_exist("Name", self.checkpoint_name(session, instance_name), data)



    def _delete(self, key_name, key):
        '''Delete a key

        Delete is idempotent. Deleting the same key multiple times does not
        raise an exception. Similarly, if the key does not exist, _delete does
        not raise an exception.

        @return the consumed capacity
        '''
        try:
            if self.debug:
                rsp = self.table.delete_item(
                    Key={key_name: key},
                    ReturnConsumedCapacity='TOTAL')

                return int(rsp['ConsumedCapacity']['CapacityUnits'])
            else:
                rsp = self.table.delete_item(Key={key_name: key})
                return 1

        except ClientError as e:
            raise e



    def delete_checkpoint(self, session, instance_name):
        return self._delete("Name", self.checkpoint_name(session, instance_name))



    def gc_sync_point_name(self, session, parent_function_instance_name):

        return f'{session}/{parent_function_instance_name}-gc'



    def fanin_sync_point_name(self, session, aggregation_function_instance_name):

        return f'{session}/{aggregation_function_instance_name}-fanin'



    def gc_sync_ready(self, session, parent_function_instance_name, index, num_branches):
        '''Mark my gc as ready and check if gc is ready to run

        In the case of a parent node invoking multiple downstream child nodes,
        all child nodes need to have created their checkpoints before the
        parent node's checkpoint can be garbage collected. Unum have all child
        nodes synchronize via the intermediate datastore so that the
        last-to-finish child node deletes the parent's checkpoint.

        The synchronization item is named by the gc_sync_point_name() function
        based on the session ID and the parent function's instance name.

        @return True is I'm the last-to-finish child node. False if I'm not.
        '''

        return self._sync_ready(self.gc_sync_point_name(session, parent_function_instance_name), index, num_branches)



    def fanin_sync_ready(self, session, aggregation_function_instance_name, index, num_branches):
        '''Mark my branch as ready and check if fan-in is ready to run

        In the case of fan-in, all upstream branches need to have created
        their checkpoints before the aggregation function is invoked. Unum
        have all branches synchronize via the intermediate datastore so that only
        the last-to-finish branch invokes the aggregation function.

        The synchronization item is named by the fanin_sync_point_name() function
        based on the session ID and the aggregation function's instance name.

        @return True is I'm the last-to-finish branch. False if I'm not.
        '''

        return self._sync_ready(self.fanin_sync_point_name(session, aggregation_function_instance_name), index, num_branches)



    def _sync_ready(self, sync_point_name, index, num_branches):
        '''Mark the caller ready and return the return map

        @param sync_point_name DynamoDB primary key of the synchronization item
        @param index caller's index in the synchronization item
        @param num_branches the number of nodes that need to synchronize
        '''
        return self._sync_ready_bitmap(sync_point_name, index, num_branches)



    def _sync_ready_bitmap(self, sync_point_name, index, num_branches):
        self._create_bitmap(sync_point_name, num_branches)
        ready_map = self._update_bitmap_result(sync_point_name, index)

        return self._bitmap_ready(ready_map)



    def _create_bitmap(self, bitmap_name, bitmap_size):

        value = {"ReadyMap": [False for i in range(bitmap_size)]}

        return self._create_if_not_exist("Name", bitmap_name, value)



    def _update_bitmap_result(self, bitmap_name, index):
        try:
            ret = self.table.update_item(
                Key={"Name": bitmap_name},
                ReturnValues='ALL_NEW',
                UpdateExpression="set #L[" + str(index) + "] = :nd",
                ConditionExpression='attribute_exists(#N)',
                ExpressionAttributeValues={':nd': True},
                ExpressionAttributeNames={"#N": "Name", "#L": "ReadyMap"})
        except Exception as e:
            raise e

        return ret['Attributes']['ReadyMap']



    def _bitmap_ready(self, bitmap):
        '''Check if the bitmap is all True
        '''

        for b in bitmap:
            if b == False:
                return False
        return True



    def _sync_ready_counter(self, sync_point_name, index, num_branches):
        pass



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


