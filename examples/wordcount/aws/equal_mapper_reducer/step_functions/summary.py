import json, os

def lambda_handler(event, context):
	ret = {}

	for chunk in event:
		for key in chunk:
			if key in ret:
				ret[key] = ret[key]+chunk[key]
			else:
				ret[key] = chunk[key]

	return ret