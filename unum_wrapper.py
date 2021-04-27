from workload import lambda_handler as app

def ingress(event, context):
	pass

def egress(output):
	return output

def lambda_handler(event, context):
	ret = app(event,context)
	return egress(ret)