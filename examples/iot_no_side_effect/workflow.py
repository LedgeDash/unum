from my_faas_functions import aggregator, hvac_controller

def lambda_handler(event, context):

	agg_ret = aggregator(event)

	action = hvac_controller(agg_ret)

	return action