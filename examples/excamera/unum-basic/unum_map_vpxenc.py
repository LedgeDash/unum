import json
import boto3

lambda_client = boto3.client("lambda")

def lambda_handler(event, context):
    for c in event['chunks']:
        response = lambda_client.invoke(
            FunctionName="excamera-unum-basic-vpxenc",
            InvocationType='Event',
            LogType='None',
            Payload=json.dumps(c),
        )
        # ret = response['Payload'].read()
    return event