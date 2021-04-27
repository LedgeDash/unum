from my_faas_functions import mapper, reducer, sort, summary

def lambda_handler(event, context):
	# event is a list of file points in JSON

	map_ret = map(mapper, event)
	reduce_ret = map(reducer, map_ret)
	return summary(reduce_ret)