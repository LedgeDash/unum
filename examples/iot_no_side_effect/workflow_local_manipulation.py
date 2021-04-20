from my_faas_functions import aggregator, hvac_controller
from datetime import datetime
import json

def lambda_handler(event, context):

	agg_ret = aggregator(event)

	agg_ret['aggregator timestamp'] = datetime.now().isoformat(timespec='milliseconds')

	payload = json.dumps(agg_ret)

	action = hvac_controller(payload)

	return action