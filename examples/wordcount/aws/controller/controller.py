import json
import boto3

client = boto3.client('lambda')

def invoke_mapper(text):
	return ret

def lambda_handler(event, context):
	
	data = event['data']
	for t in data:
		invoke_mapper(t)