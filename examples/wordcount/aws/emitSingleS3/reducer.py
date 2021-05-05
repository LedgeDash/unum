from user_reduce import user_reduce
import mapreduce as mr

def lambda_handler(event, context):
    bucket = event['bucket']
    partition = event['partition']

    data = mr.readPerReducerSingle(bucket, partition)

    ret = {}
    for k in data:
        ret[k] = user_reduce(k, data[k])

    return ret