import argparse
import os, sys

def mapper(data):

    words = data.split()

    ret = [(word, 1) for word in words]

    return ret

def reducer(data):
	ret = {}

	for item in data:
		if item[0] in ret:
			ret[item[0]] = ret[item[0]]+item[1]
		else:
			ret[item[0]] = 1

	return ret

def main():
	parser = argparse.ArgumentParser(description='word count')
	parser.add_argument('input_file')
	args = parser.parse_args()

	with open(args.input_file) as f:
		data = f.read()

	map_ret = mapper(data)
	reduce_ret = reducer(map_ret)
	print(reduce_ret)

if __name__ == '__main__':
	main()