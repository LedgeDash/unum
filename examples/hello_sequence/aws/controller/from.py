def lambda_handler(event, context):
	data = event['data']
	ret = data + ' from'
	return {'data': ret}