from my_faas_functions import mapper, reducer, sort, summary, splitter

def lambda_handler(event, context):
	# event is a single file

	file_list = splitter(event)
	map_ret = map(mapper, file_list)
	reduce_ret = map(reducer, map_ret)
	return summary(reduce_ret)