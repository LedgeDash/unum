from my_faas_functions import aggregator_raw_data_no_se, hvac_controller_raw_data_no_se
import requests, json

def handle(event):
	'''This function is expected to be invoked via HTTP requests, not S3
	events
	'''
	action = hvac_controller_raw_data_no_se(aggregator_raw_data_no_se(json.dumps(event)))

	requests.get(actuator_url, data = action)