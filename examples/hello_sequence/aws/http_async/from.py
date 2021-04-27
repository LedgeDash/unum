import boto3
import json

client = boto3.client('lambda')

def lambda_handler(event, context):
    data = event['data']
    ret = data + ' from'
    response = client.invoke(
        FunctionName='shandong-http-async',
        InvocationType='Event',
        LogType='None',
        Payload=json.dumps({'data': ret}),
    )

    ret = response['Payload'].read()