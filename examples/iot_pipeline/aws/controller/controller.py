import boto3
import json

client = boto3.client('lambda')

def lambda_handler(event, context):

    response = client.invoke(
        FunctionName='aggregator-controller',
        LogType='None',
        Payload=json.dumps(event),
    )

    ret = response['Payload'].read()
    response['Payload'].close()

    response = client.invoke(
        FunctionName='hvac_controller-controller',
        LogType='None',
        Payload=ret,
    )

    ret = response['Payload'].read()
    response['Payload'].close()

    return ret