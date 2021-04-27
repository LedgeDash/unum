from datetime import datetime
import boto3
import json

client = boto3.client('lambda')

def lambda_handler(event, context):
    data = event['data']
    ret = data + datetime.today().strftime('%Y-%m-%d')

    return {'data': ret}