# This version expects `event` to be an asynchronous invocation event from an
# aggregator function on success.
#
# Incompatible triggers include
# 1. S3 events
# 2. SNS messages
# 3. boto3 sync
# 4. boto3 async
# 5. aws lambda invoke

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
