import csv
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import sys, json
import argparse
from operator import itemgetter

def main():
    parser = argparse.ArgumentParser(description='Analyze the Parallel Pipeline Step Functions performance')
    parser.add_argument('experiment_results')
    args = parser.parse_args()
    
    with open(args.experiment_results) as f:
        data = json.loads(f.read())

    for d in data:

        depth = d['depth']
        depth_result = d['results']

        fanOutSizes = [e['fan-out size'] for e in depth_result]
        avgLatencyPerFanOutSize = []
        stdevPerFanOutSize = []
        for fanOutSize in depth_result:
            fanOutResult = fanOutSize['results']
            rawLatencies = [e['e2eLatency'] for e in fanOutResult if e['succeed']]
            rawLatencies.sort()
            rawLatencies.remove(rawLatencies[0])
            rawLatencies.remove(rawLatencies[-1])

            avgLatencyPerFanOutSize.append(np.mean(rawLatencies))
            stdevPerFanOutSize.append(np.std(rawLatencies))


        fanOutSizes.reverse()
        avgLatencyPerFanOutSize.reverse()
        stdevPerFanOutSize.reverse()
        fanOutSizes = np.array(fanOutSizes)
        avgLatencyPerFanOutSize = np.array(avgLatencyPerFanOutSize)
        stdevPerFanOutSize = np.array(stdevPerFanOutSize)

        np.savetxt("fanOutSizes.csv",fanOutSizes, delimiter=",")
        np.savetxt("avgLatencyPerFanOutSize.csv",avgLatencyPerFanOutSize, delimiter=",")
        np.savetxt("stdevPerFanOutSize.csv",stdevPerFanOutSize, delimiter=",")

        print(fanOutSizes)
        print(avgLatencyPerFanOutSize)
        print(stdevPerFanOutSize)

        fig, ax = plt.subplots()
        ax.grid()
        ax.errorbar(fanOutSizes, avgLatencyPerFanOutSize,
        	        yerr=stdevPerFanOutSize,
                    fmt='-o')
        # ax.plot(fanOutSizes,avgLatencyPerFanOutSize, '-o')
        fig.savefig("e2e_latency-1-1000.png")

        fig, ax = plt.subplots()
        ax.grid()
        # ax.plot(fanOutSizes[0:10],avgLatencyPerFanOutSize[0:10], '-o')
        ax.errorbar(fanOutSizes[0:10], avgLatencyPerFanOutSize[0:10],
        	        yerr=stdevPerFanOutSize[0:10],
                    fmt='-o')
        fig.savefig("e2e_latency-1-18.png")

        fig, ax = plt.subplots()
        ax.grid()
        # ax.plot(fanOutSizes[0:11],avgLatencyPerFanOutSize[0:11], '-o')
        ax.errorbar(fanOutSizes[0:11], avgLatencyPerFanOutSize[0:11],
        	        yerr=stdevPerFanOutSize[0:11],
                    fmt='-o')
        fig.savefig("e2e_latency-1-20.png")

        fig, ax = plt.subplots()
        ax.grid()
        # ax.plot(fanOutSizes[0:36],avgLatencyPerFanOutSize[0:36], '-o')
        ax.errorbar(fanOutSizes[0:36], avgLatencyPerFanOutSize[0:36],
        	        yerr=stdevPerFanOutSize[0:36],
                    fmt='-o')
        fig.savefig("e2e_latency-1-100.png")

        fig, ax = plt.subplots()
        ax.grid()
        # ax.plot(fanOutSizes[36:],avgLatencyPerFanOutSize[36:], '-o')
        ax.errorbar(fanOutSizes[36:], avgLatencyPerFanOutSize[36:],
        	        yerr=stdevPerFanOutSize[36:],
                    fmt='-o')
        fig.savefig("e2e_latency-100-1000.png")

        fig, ax = plt.subplots()
        ax.grid()
        # ax.plot(fanOutSizes[36:],avgLatencyPerFanOutSize[36:], '-o')
        x_idx = [0,25] + list(range(35,len(fanOutSizes)))
        ax.errorbar([fanOutSizes[i] for i in x_idx], [avgLatencyPerFanOutSize[i] for i in x_idx],
        	        yerr=[stdevPerFanOutSize[i] for i in x_idx],
                    fmt='-o')
        fig.savefig("e2e_latency-1-1000-50incr.png")


if __name__ == '__main__':
    main()