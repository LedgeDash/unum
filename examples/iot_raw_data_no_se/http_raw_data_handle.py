from my_faas_functions import aggregator_raw_data_no_se, hvac_controller_raw_data_no_se
import requests, json

actuator_url='https://my-actuator.iot'

def adjust_actuator(action):
	requests.get(actuator_url, data = action)
	return actuator_url

def handle(event):
	'''This function is expected to be invoked via HTTP requests, not S3
	events
	'''
	action = hvac_controller_raw_data_no_se(aggregator_raw_data_no_se(json.dumps(event)))

	return adjust_actuator(action)
