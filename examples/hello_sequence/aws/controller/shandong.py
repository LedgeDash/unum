def lambda_handler(event, context):
	data = event['data']
	ret = data + ' Shandong.'
	return {'data': ret}