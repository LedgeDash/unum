import json

def lambda_handler(event, context):
	ret = {}

	for item in event:
		if item[0] in ret:
			ret[item[0]] = ret[item[0]]+1
		else:
			ret[item[0]] = 1

	return ret