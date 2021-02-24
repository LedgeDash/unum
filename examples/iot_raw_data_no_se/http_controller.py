import json, boto3
import requests

client = boto3.client('lambda')

def hvac_controller_raw_data_no_se(data):
	response = client.invoke(
		FunctionName ='arn:aws:lambda:eu-west-1:890277245818:function:hvac_controller_raw_data_no_se',
		InvocationType ='RequestResponse',
		Payload = json.dumps(data)
		)

	return json.load(response['Payload'])

def aggregator_raw_data_no_se(data):
	response = client.invoke(
		FunctionName ='arn:aws:lambda:eu-west-1:890277245818:function:aggregator_raw_data_no_se',
		InvocationType ='RequestResponse',
		Payload = json.dumps(data)
		)

	return json.load(response['Payload'])

def handle(event):
	'''This function is expected to be invoked via HTTP requests, not S3 events
	'''
	action = hvac_controller_raw_data_no_se(aggregator_raw_data_no_se(event))

	requests.get(actuator_url, data = json.dumps(action))