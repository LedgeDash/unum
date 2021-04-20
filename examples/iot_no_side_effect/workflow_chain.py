from my_faas_functions import aggregator, hvac_controller

def lambda_handler(event, context):

	action = hvac_controller(aggregator(event))

	return action