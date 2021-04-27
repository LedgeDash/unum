import json
import boto3

client = boto3.client('lambda')

def lambda_handler(event, context):

    response = client.invoke(
        FunctionName='wc-map-controller',
        LogType='None',
        Payload=json.dumps(event),
    )

    ret = response['Payload'].read()

    response = client.invoke(
        FunctionName='wc-reduce-controller',
        LogType='None',
        Payload=ret,
    )

    ret = response['Payload'].read()
    return