# To automate testing parallel pipeline Step Functions. Currently there are 10
# deployed Step Functions each with a different pipeline depth ranging from 1
# to 10. For each

import argparse
import subprocess
import json
import time
from datetime import datetime

MAX_DEPTH = 10
PARALLEL_PIPELINE_SF_PREFIX="arn:aws:states:us-east-1:746167823857:stateMachine:parallel-pipeline-depth"
def createFanOutInputJson(fanOutSize):
	payload=[{"text": "hello "} for i in range(fanOutSize)]
	ret = {"data":payload}
	return json.dumps(ret)

def startSfExecution(sfArn, inputData):
	"""`aws stepfunctions start-execution` returns a JSON string that contains
	the executionArn and the start timestamp. We can use the executionArn to
	acquire the completion timestamp and the entire execution history later.

	This function returns the `aws stepfunctions start-execution` output as a
	python dict.
	"""
	ret = subprocess.run(["aws",
		"stepfunctions",
		"start-execution",
		"--state-machine-arn", sfArn,
		"--input", inputData],
		capture_output=True)

	return json.loads(ret.stdout)

def describeExecution(executionArn):
	ret = subprocess.run(["aws",
		"stepfunctions",
		"describe-execution",
		"--execution-arn", executionArn],
		capture_output=True)

	return json.loads(ret.stdout)


def startParallelPipelineExecution(depth, fanOutSize):
	"""start a parallel pipeline Step Function execution with a particular
	pipeline depth and fan-out size.

	depth: pipeline depth
	fanOutSize: # of parallel tasks

	return: a dict with the following fields
	sfArn: str
	executionArn: str
	succeed: bool
	e2eLatency: int
	"""
	if depth > MAX_DEPTH:
		raise IOError(f'depth needs to be less than {MAX_DEPTH}. Got {depth}.')

	sfArn = PARALLEL_PIPELINE_SF_PREFIX+str(depth)
	inputData = createFanOutInputJson(fanOutSize)

	executionStartRet = startSfExecution(sfArn, inputData)
	executionArn = executionStartRet["executionArn"]

	ret = {"sfArn": sfArn, "executionArn":executionArn}

	executionInfo = {}
	executionInfo["status"] = "RUNNING"

	while executionInfo["status"] != "SUCCEEDED":
		time.sleep(2)
		executionInfo = describeExecution(executionArn)

		if executionInfo["status"] == "FAILED":
			ret["succeed"]=False
			return ret
			# break

	startTimestamp = datetime.fromisoformat(executionInfo["startDate"])
	stopTimestamp = datetime.fromisoformat(executionInfo["stopDate"])
	delta = stopTimestamp - startTimestamp
	e2eLatency = delta.seconds*1000+delta.microseconds/1000

	ret["succeed"] = True
	ret["e2eLatency"] = e2eLatency

	return ret

def main():

	# pre-warm the Lambdas by running 1000 fan-outs at depth 1
	# print(f'First warm: {startParallelPipelineExecution(1,1000)}')
	# time.sleep(2)
	# print(f'Second warm: {startParallelPipelineExecution(1,1000)}')

	ITER = 2 # For a particular (depth, fanOutSize) setup, how many iterations of experiment we run
	results = []

	for depth in range(10,11):

		depthResult = {"depth": depth, "results": []}
		# print(f'pipeline depth: {depth}')

		# fanOutSizes = [i for i in range(0, 51, 2)] + [i for i in range(55, 101, 5)]+ [i for i in range(150, 1001, 50)]
		# fanOutSizes = [i for i in range(0, 51, 2)] + [i for i in range(55, 101, 5)]
		fanOutSizes = [i for i in range(0, 51, 2)]
		# fanOutSizes = [i for i in range(42, 51, 2)]
		# fanOutSizes = [i for i in range(100, 501, 50)]
		fanOutSizes[0] = 1

		fanOutSizes.reverse()

		for fanOutSize in fanOutSizes:
			# print(f'fan-out size: {fanOutSize}')
			fanOutSizeResult = {"fan-out size": fanOutSize, "results": []}
			for e in range(0, ITER):
				ret = startParallelPipelineExecution(depth,fanOutSize)
				fanOutSizeResult["results"].append(ret)
				time.sleep(5)

			depthResult["results"].append(fanOutSizeResult)
			time.sleep(10)

		results.append(depthResult)

	print(f"{json.dumps(results)}")

if __name__ == '__main__':
	main()