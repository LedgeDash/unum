from datetime import datetime

def lambda_handler(event, context):
	data = event['data']
	ret = data + ' ' + datetime.today().strftime('%Y-%m-%d')
	
	return {'data': ret}