from my_faas_functions import aggregator, hvac_controller
from datetime import datetime

def local_func(input):
	return input

def lambda_handler(event, context):

	event['input timestamp'] = datetime.now().isoformat(timespec='milliseconds')

	agg_ret = aggregator(event)

	agg_ret['aggregator timestamp'] = datetime.now().isoformat(timespec='milliseconds')

	payload = local_func(agg_ret)

	action = hvac_controller(payload)

	return action