import json

def handle(data):
	ret = {}

	for item in data:
		if item[0] in ret:
			ret[item[0]] = ret[item[0]]+item[1]
		else:
			ret[item[0]] = 1

	return ret