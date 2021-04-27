import boto3
import json

client = boto3.client('lambda')

def lambda_handler(event, context):
    data = {'data': 'Hello'}

    response = client.invoke(
        FunctionName='from-http-async',
        InvocationType='Event',
        LogType='None',
        Payload=json.dumps(data),
    )

    ret = response['Payload'].read()

    