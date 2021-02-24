from my_faas_functions import aggregator_raw_data_no_se, hvac_controller_raw_data_no_se
import requests
import boto3
from urllib.parse import unquote_plus

def get_data(request):

    with open(request) as f:
        data = f.read()
        return data

def handle(event):
	'''This function is expected to be invoked via S3 events, not HTTP
	requests
	'''
	s3_client = boto3.client('s3')

	record = event['Records']
	bucket = record['s3']['bucket']['name']
    key = unquote_plus(record['s3']['object']['key'])

    download_path = '/tmp/{}{}'.format(uuid.uuid4(), tmpkey)
    s3_client.download_file(bucket, key, download_path)

    with open(download_path) as f:
        data = f.read()

	action = hvac_controller_raw_data_no_se(aggregator_raw_data_no_se(data))

	requests.get(actuator_url, data = action)