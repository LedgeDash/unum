import boto3
import json
lambda_client = boto3.client("lambda")

def invoke_lambda(data, function_name):

    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='Event',
        LogType='None',
        Payload=json.dumps(data),
    )
    ret = response['Payload'].read()

    return

def lambda_handler(event, context):
    print(event)
    print(context.__dict__)
    failed_function = event['requestContext']['functionArn']
    failed_input = event['requestPayload']

    retry_input = failed_input
    if "Retry Number" in failed_input:
        retry_input["Retry Number"] = failed_input["Retry Number"]+1
    else:
        retry_input["Retry Number"] = 1

    retry_input["ErrorType"] = "Runtime"
    retry_input["ErrorMessage"] = event['responsePayload']['errorMessage']
    retry_input["StackTrace"] = event['responsePayload']['stackTrace']

    invoke_lambda(retry_input, failed_function)
    
    print(retry_input)