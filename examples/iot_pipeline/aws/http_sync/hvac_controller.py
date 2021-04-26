# This version expects the raw input in the `event` input parameter.
# Therefore, it can only be invoked via HTTP requests (synchronous or
# asynchronous). This means the compatible triggers are:
# 1. boto3 sync
# 2. boto3 async
# 3. aws lambda invoke
#
# Incompatible triggers include
# 1. S3 events
# 2. SNS messages
# 3. Destination

from datetime import datetime
import json

THRESHOLD = 1
actuator_url='https://my-actuator.iot'

def lambda_handler(event, context):
	average = event['average_power_consumption']

	command = 0

	if average > THRESHOLD:
		command = 1

	action = {
		"timestamp": datetime.now().isoformat(timespec='milliseconds'),
		"reduce_power": command
	}

	return action

