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
	args = parser.parse_args()
	
	with open(args.first_function_log) as f:
		r = csv.reader(f)
		first_function_tsp = process(r)

	with open(args.second_function_log) as f:
		r = csv.reader(f)
		second_function_tsp = process(r)

	assert(len(first_function_tsp) == len(second_function_tsp))

	# Calculate the runtime duration
	first_function_runtime = np.array([(first_function_tsp[i][1] - first_function_tsp[i][0]) for i in range(len(first_function_tsp))])
	second_function_runtime = np.array([(second_function_tsp[i][1] - second_function_tsp[i][0]) for i in range(len(second_function_tsp))])

	fig, axs = plt.subplots(1, 2, tight_layout=True, sharey=True)

	axs[0].set_title('first_function runtime')
	axs[0].scatter(np.array([i for i in range(len(first_function_runtime))]), first_function_runtime)
	axs[0].text(0.4, 0.9, '$\mu=${:.2f}, $\sigma=${:.2f}'.format(np.mean(first_function_runtime), np.std(first_function_runtime)), transform=axs[0].transAxes)
	axs[0].set_xlabel('iteration')
	axs[0].set_ylabel('latency (ms)')

	axs[1].set_title('second_function runtime')
	axs[1].scatter(np.array([i for i in range(len(second_function_runtime))]), second_function_runtime)
	axs[1].text(0.4, 0.9, '$\mu=${:.2f}, $\sigma=${:.2f}'.format(np.mean(second_function_runtime), np.std(second_function_runtime)), transform=axs[1].transAxes)

	fig.savefig('runtime.png')

	# Calculate communication latency

	# first_start_to_second_start also includes the computation that the first
	# function performs before invoking the second function. So this may not
	# be accurate for compute-heavy functions, such as map in word count.
	first_start_to_second_start = np.array([(second_function_tsp[i][0] - first_function_tsp[i][0]) for i in range(len(first_function_tsp))])
	second_end_to_first_end = np.array([(first_function_tsp[i][1] - second_function_tsp[i][1]) for i in range(len(first_function_tsp))])

	fig, axs = plt.subplots(1, 2, tight_layout=True, sharey=True)
	axs[0].set_title('1st start to 2nd start')
	axs[0].scatter(np.array([i for i in range(len(first_start_to_second_start))]), first_start_to_second_start)
	axs[0].text(0.4,0.9, '$\mu=${:.2f}, $\sigma=${:.2f}'.format(np.mean(first_start_to_second_start), np.std(first_start_to_second_start)), transform=axs[0].transAxes)
	axs[0].set_xlabel('iteration')
	axs[0].set_ylabel('latency (ms)')

	axs[1].set_title('2nd end to 1st end')
	axs[1].scatter(np.array([i for i in range(len(second_end_to_first_end))]), second_end_to_first_end)
	axs[1].set_xlabel('iteration')
	axs[1].text(0.4,0.9, '$\mu=${:.2f}, $\sigma=${:.2f}'.format(np.mean(second_end_to_first_end), np.std(second_end_to_first_end)), transform=axs[1].transAxes)

	fig.savefig('communication latency.png')

	# end-to-end latency

	e2e_latency = np.array([second_function_tsp[i][1] - first_function_tsp[i][0] for i in range(len(second_function_tsp))])

	e2e_mean = np.mean(e2e_latency)
	e2e_stdev = np.std(e2e_latency)

	fig, ax = plt.subplots()
	ax.scatter(np.array([i for i in range(len(e2e_latency))]), e2e_latency)
	ax.set(xlabel='iteration', ylabel='latency (ms)',
	       title='end-to-end latency')
	ax.text(0.4,0.9, '$\mu=${:.2f}, $\sigma=${:.2f}'.format(e2e_mean, e2e_stdev), transform=ax.transAxes)
	ax.grid()

	fig.savefig("e2e_latency.png")

if __name__ == '__main__':
	main()