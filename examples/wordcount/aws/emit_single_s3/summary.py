
def lambda_handler(event, context):
	ret = {}
	for d in event:
		ret.update(d)

	return ret