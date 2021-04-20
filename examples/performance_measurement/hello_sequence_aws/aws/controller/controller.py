import boto3
import json

client = boto3.client('lambda')

def lambda_handler(event, context):

    response = client.invoke(
        FunctionName='hello-controller',
        LogType='None'
    )

    ret = response['Payload'].read()

    response = client.invoke(
        FunctionName='from-controller',
        LogType='None',
        Payload=ret,
    )

    ret = response['Payload'].read()

    response = client.invoke(
        FunctionName='shandong-controller',
        LogType='None',
        Payload=ret,
    )

    ret = response['Payload'].read()

    response = client.invoke(
        FunctionName='today-controller',
        LogType='None',
        Payload=ret,
    )

    ret = response['Payload'].read()

    return ret