import csv
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import sys
import argparse

def process(f):
	'''Given a CloudWatch log csv file descriptor, return a list of tuples
	with each tuple being (START timestamp, END timestamp) of a Lambda
	invocation'''
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
	parser.add_argument('controller_log')
	args = parser.parse_args()
	
	with open(args.first_function_log) as f:
		r = csv.reader(f)
		aggregator_tsp = process(r)

	with open(args.second_function_log) as f:
		r = csv.reader(f)
		hvac_tsp = process(r)

	with open(args.controller_log) as f:
		r = csv.reader(f)
		controller_tsp = process(r)

	assert(len(aggregator_tsp) == len(hvac_tsp) == len(controller_tsp))

	# Calculate the runtime duration
	aggregator_runtime = np.array([(aggregator_tsp[i][1] - aggregator_tsp[i][0]) for i in range(len(aggregator_tsp))])
	hvac_runtime = np.array([(hvac_tsp[i][1] - hvac_tsp[i][0]) for i in range(len(hvac_tsp))])

	fig, axs = plt.subplots(1, 2, tight_layout=True, sharey=True)

	axs[0].set_title('aggregator runtime')
	axs[0].scatter(np.array([i for i in range(len(aggregator_runtime))]), aggregator_runtime)
	axs[0].text(0, 0, '$\mu=${:.2f}, $\sigma=${:.2f}'.format(np.mean(aggregator_runtime), np.std(aggregator_runtime)))
	axs[0].set_xlabel('iteration')
	axs[0].set_ylabel('latency (ms)')

	axs[1].set_title('hvac_controller runtime')
	axs[1].scatter(np.array([i for i in range(len(hvac_runtime))]), hvac_runtime)
	axs[1].text(0, 0, '$\mu=${:.2f}, $\sigma=${:.2f}'.format(np.mean(hvac_runtime), np.std(hvac_runtime)))

	fig.savefig('runtime.png')

	# Calculate the invocation latency

	latency = np.array([(hvac_tsp[i][0] - aggregator_tsp[i][1]) for i in range(len(aggregator_tsp))])
	mean = np.mean(latency)
	stdev = np.std(latency)

	n_bins = 60
	fig, axs = plt.subplots(1, 2, tight_layout=True)
	axs[0].set_title('invocation latency')
	axs[0].scatter(np.array([i for i in range(len(latency))]), latency)
	axs[1].hist(latency, bins=n_bins)

	axs[0].set_xlabel('iteration')
	axs[0].set_ylabel('latency (ms)')

	axs[1].set_xlabel('latency (ms)')
	axs[1].set_ylabel('count')
	axs[1].text(30, 20, '$\mu=${:.2f}, $\sigma=${:.2f}'.format(mean, stdev))

	fig.savefig('invocation_latency.png')

	print('mean: {}'.format(np.mean(latency)))
	print('stdev: {}'.format(np.std(latency)))


	e2e_latency = np.array([controller_tsp[i][1] - controller_tsp[i][0] for i in range(len(controller_tsp))])

	e2e_mean = np.mean(e2e_latency)
	e2e_stdev = np.std(e2e_latency)

	print('End-to-end mean: {}'.format(e2e_mean))
	print('End-to-end stdev: {}'.format(e2e_stdev))

	fig, ax = plt.subplots()
	ax.scatter(np.array([i for i in range(len(e2e_latency))]), e2e_latency)

	ax.set(xlabel='iteration', ylabel='latency (ms)',
	       title='end-to-end latency')
	ax.text(170, 120, '$\mu=${:.2f}, $\sigma=${:.2f}'.format(e2e_mean, e2e_stdev))
	ax.grid()

	fig.savefig("e2e_latency.png")

	iot_start_to_agg_start = np.array([aggregator_tsp[i][0] - controller_tsp[i][0]  for i in range(len(controller_tsp))])
	print('To agg mean: {}'.format(np.mean(iot_start_to_agg_start)))
	print('To agg stdev: {}'.format(np.std(iot_start_to_agg_start)))


	hvac_end_to_iot_end = np.array([controller_tsp[i][1] - hvac_tsp[i][1] for i in range(len(controller_tsp))])
	print('From hvac mean: {}'.format(np.mean(hvac_end_to_iot_end)))
	print('From hvac  stdev: {}'.format(np.std(hvac_end_to_iot_end)))

if __name__ == '__main__':
	main()