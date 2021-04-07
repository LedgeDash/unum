import csv
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt


def process(f):
	timestamps = [row[0] for row in r if row[1].startswith('START') or row[1].startswith('END') ]
	i=0
	ret = []
	while i < len(timestamps):
		ret.append((int(timestamps[i]), int(timestamps[i+1])))
		i = i+2

	return ret


with open('aggregator-destination.csv') as f:
	r = csv.reader(f)
	aggregator_tsp = process(r)

with open('hvac_controller-destination.csv') as f:
	r = csv.reader(f)
	hvac_tsp = process(r)

assert(len(aggregator_tsp) == len(hvac_tsp))

latency = np.array([(hvac_tsp[i][0] - aggregator_tsp[i][1]) for i in range(len(aggregator_tsp))])
print('mean: {}'.format(np.mean(latency)))
print('stdev: {}'.format(np.std(latency)))

n_bins = 60
fig, axs = plt.subplots(1, 2, tight_layout=True)
axs[0].scatter(np.array([i for i in range(len(latency))]), latency)
axs[1].hist(latency, bins=n_bins)

axs[0].set_xlabel('iteration')
axs[0].set_ylabel('latency (ms)')

axs[1].set_xlabel('latency (ms)')
axs[1].set_ylabel('count')

fig.savefig('destination-latency.png')