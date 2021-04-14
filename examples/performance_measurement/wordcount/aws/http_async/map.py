import json
import boto3

client = boto3.client('lambda')

def lambda_handler(event, context):
    text = event['data']

    words = text.split()

    ret = [(word, 1) for word in words]

    response = client.invoke(
        FunctionName='wc-reduce-http-async',
        # InvocationType='Event',
        LogType='None',
        Payload=json.dumps(ret),
    )

    ret = response['Payload'].read()

    return
