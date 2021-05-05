import uuid
import hashlib
import os
import boto3
s3_client = boto3.client('s3')

perWordRet = {}

numReducer = 3
perReducerRet = {}
destinationBucket = ""


for i in range(numReducer):
    perReducerRet[f'reducer{i}'] = {}


def emitPerReducerSingle(word):
    # create a file in S3 with name reducer{reducerId}/{word}/{uuid}
    reducerId = int(hashlib.sha256(word.encode('utf-8')).hexdigest(), 16) % numReducer
    fileUuid = uuid.uuid4()
    objKey = f'reducer{reducerId}/{word}/{fileUuid}'

    local_file_path = f'/tmp/{fileUuid}.tmp'

    with open(local_file_path, 'w'):
        os.utime(local_file_path, None)

    s3_client.upload_file(local_file_path, destinationBucket, objKey)


def emitPerReducerBuffer(word):
    # Instead of calling s3.upload_flle for every word occurrence, buffer
    # mapper output locally in memory.
    reducerId = int(hashlib.sha256(word.encode('utf-8')).hexdigest(), 16) % numReducer
    if word in perReducerRet[f'reducer{reducerId}']:
        perReducerRet[f'reducer{reducerId}'][word].append(1)
    else:
        perReducerRet[f'reducer{reducerId}'][word] = [1]

    # we could add logic here to periodically write parts of the result to
    # storage

def outputPerReducerBuffer():
    # Write the local mapper output buffer to S3.
    # For each word, write a single file named reducer{id}/{word}/{uuid}
    # The content of the file is a json list of 1's.
    if perReducerRet == {}:
        return
    print(perReducerRet)

def readPerReducerSingle(bucket, partition):
    # Given a bucket and partition (e.g., reducer0/), return a map whose keys
    # are words in the partition and values are list of 1's, one for each
    # occurrence of the word. This function assumes that the files creates by
    # emitPerReducerSingle. In other words, the s3 directory should have a
    # list of subdirectories, one for each word. And under each word's
    # directory, there should be a list of uuid-named files, one for each
    # occurrence. These files do not have any contents.
    
    response = s3_client.list_objects(
        Bucket=bucket,
        Prefix=partition # e.g., reducer0/
    )

    data = [e['Key'] for e in response['Contents']]

    data = [e.split('/')[1:] for e in data]

    ret = {}
    for e in data:
        if e[0] in ret:
            ret[e[0]].append(1)
        else:
            ret[e[0]] = [1]
    return ret