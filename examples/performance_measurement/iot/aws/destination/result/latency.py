import csv
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import sys
import argparse

def pre_process(f):
	timestamps = [row[0] for row in f if row[1].startswith('START') or row[1].startswith('END') ]
	i=0
	ret = []
	while i < len(timestamps):
		ret.append((int(timestamps[i]), int(timestamps[i+1])))
		i = i+2

	return ret

def main():

	parser = argparse.ArgumentParser(description='Process CloudWatch logs for a 2-function pipeline')
	parser.add_argument('first_function_log')
	parser.add_argument('second_function_log')
	args = parser.parse_args()
	
	with open(args.first_function_log) as f:
		r = csv.reader(f)
		aggregator_tsp = pre_process(r)

	with open(args.second_function_log) as f:
		r = csv.reader(f)
		hvac_tsp = pre_process(r)

	assert(len(aggregator_tsp) == len(hvac_tsp))

	latency = np.array([(hvac_tsp[i][0] - aggregator_tsp[i][1]) for i in range(len(aggregator_tsp))])
	mean = np.mean(latency)
	stdev = np.std(latency)

	n_bins = 60
	fig, axs = plt.subplots(1, 2, tight_layout=True)
	axs[0].scatter(np.array([i for i in range(len(latency))]), latency)
	axs[1].hist(latency, bins=n_bins)

	axs[0].set_xlabel('iteration')
	axs[0].set_ylabel('latency (ms)')

	axs[1].set_xlabel('latency (ms)')
	axs[1].set_ylabel('count')
	axs[1].text(250, 30, '$\mu=${:.2f}, $\sigma=${:.2f}'.format(mean, stdev))

	fig.savefig('result.png')

	print('mean: {}'.format(np.mean(latency)))
	print('stdev: {}'.format(np.std(latency)))

if __name__ == '__main__':
	main()