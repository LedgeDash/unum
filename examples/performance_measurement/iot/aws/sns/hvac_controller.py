# This version expects the input `event` to be an SNS message.
# This means the compatible triggers are:
# 1. SNS messages
#
# Incompatible triggers include
# 1. S3 events
# 2. Destination
# 3. boto3 sync
# 4. boto3 async
# 5. aws lambda invoke

from datetime import datetime
import json

THRESHOLD = 1
actuator_url='https://my-actuator.iot'

def lambda_handler(event, context):
	for record in event['Records']:
		data = record['Sns']['Message']
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

