# This version expects the input `event` to be an s3 event JSON. This means
# the compatible triggers are:
# 1. S3 events
#
# Incompatible triggers include
# 1. boto3 sync
# 2. boto3 async
# 3. aws lambda invoke
# 4. SNS messages
# 5. Destination

from datetime import datetime
import boto3
import uuid
from urllib.parse import unquote_plus
import json

s3_client = boto3.client('s3')

THRESHOLD = 1
actuator_url='https://my-actuator.iot'

def lambda_handler(event, context):
	for record in event['Records']:
		bucket = record['s3']['bucket']['name']
		key = unquote_plus(record['s3']['object']['key'])

		tmpkey = key.replace('/', '')
		download_path = '/tmp/{}{}'.format(uuid.uuid4(), tmpkey)

		s3_client.download_file(bucket, key, download_path)

		with open(download_path) as f:
			data = f.read()
			payload = json.loads(data)

			average = payload['average_power_consumption']

			command = 0

			if average > THRESHOLD:
				command = 1

			action = {
				"timestamp": datetime.now().isoformat(timespec='milliseconds'),
				"reduce_power": command
			}

			return action

