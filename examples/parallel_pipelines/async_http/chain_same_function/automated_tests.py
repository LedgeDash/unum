# To automate testing parallel pipeline Step Functions. Currently there are 10
# deployed Step Functions each with a different pipeline depth ranging from 1
# to 10. For each

import argparse
import subprocess
import json
import time
from datetime import datetime

MAX_WAIT_TIME = 200
WAIT_TIME_INCR = 5
MAX_DEPTH = 10
UNUM_MAP_ARN="arn:aws:lambda:us-west-1:746167823857:function:parallel-pipeline-unum_map-async-http"
UNUM_MAP_NAME="parallel-pipeline-unum_map-async-http"
DYNAMODB_NAME='unum_intermediary_table'

def createFanOutInputJson(fanOutSize):
    payload=[{"text": "hello "} for i in range(fanOutSize)]
    ret = {"data":payload}

    return json.dumps(ret)

def startUnumExecution(firstLambda, inputData):
    ret = subprocess.run(["aws",
        "lambda",
        "invoke",
        "--function-name", firstLambda,
        "--invocation-type", "Event",
        "--payload", inputData,
        "--cli-binary-format", "raw-in-base64-out",
        "out"],
        capture_output=True)
    return ret.stdout

def updatefchainDepth(depth):
    with open('fchain/unum_config.json','r+') as f:
        config = json.load(f)
        config['depth'] = depth
        f.seek(0)
        f.write(json.dumps(config))

    ret = subprocess.run(["make", "update"],
        capture_output=True)

def startParallelPipelineExecution(fanOutSize):
    inputData = createFanOutInputJson(fanOutSize)
    return startUnumExecution(UNUM_MAP_NAME, inputData)

def deleteAllItems(tableName):
    items = listAllItems(tableName)
    for e in items:
        key = '{"sessionID":'+ json.dumps(e['sessionID'])+'}'
        ret = subprocess.run(["aws",
        "dynamodb",
        "delete-item",
        "--table-name", tableName,
        "--key", key],
        capture_output=True)

def listAllItems(tableName):
    ret = subprocess.run(["aws",
        "dynamodb",
        "scan",
        "--table-name", tableName],
        capture_output=True)
    queryRet = json.loads(ret.stdout)
    items = queryRet['Items']
    return items

def main():

    # make sure the return value dynamodb table is empty
    deleteAllItems(DYNAMODB_NAME)

    results = []

    ITER = 10 # For a particular (depth, fanOutSize) setup, how many iterations of experiment we run
    for depth in range(1,2):
        print(f'depth: {depth}')
        updatefchainDepth(depth)
        time.sleep(1)
        depthResult = {"depth": depth, "results": []}
        # fanOutSizes = [i for i in range(0, 51, 2)] + [i for i in range(55, 101, 5)]
        # fanOutSizes = [0,30]
        fanOutSizes = [i for i in range(12,51, 2)] + [i for i in range(55, 101, 5)]
        # fanOutSizes[0] = 1
        fanOutSizes.reverse()

        for fanOutSize in fanOutSizes:
            print(f'\tfanOutSize: {fanOutSize}')
            fanOutSizeResult = {"fan-out size": fanOutSize, "results": []}
            for e in range(0,ITER):

                deleteAllItems(DYNAMODB_NAME)
                time.sleep(1)

                clientStartTsp = datetime.now().isoformat()
                startParallelPipelineExecution(fanOutSize)
                
                currCount = 0
                waitTime = 0
                while currCount < fanOutSize and waitTime< MAX_WAIT_TIME:
                    time.sleep(WAIT_TIME_INCR)
                    items = listAllItems(DYNAMODB_NAME)
                    if len(items)>1:
                        raise IOError(f'more than one item in the table')

                    currCount = int(items[0]['count']['N'])
                    waitTime+=WAIT_TIME_INCR


                if int(items[0]['count']['N']) != fanOutSize:
                    print(f"[WARN] count = {items[0]['count']['N']}; fanOutSize = {fanOutSize}")
                if 'lastTSP' in items[0]:
                    ret = {'client start tsp': clientStartTsp, 'last lambda DB write tsp': items[0]['lastTSP']['S']}
                    fanOutSizeResult['results'].append(ret)

                time.sleep(5)

            depthResult["results"].append(fanOutSizeResult)
            time.sleep(2)

        results.append(depthResult)

    print(f"{json.dumps(results)}")
if __name__ == '__main__':
    main()