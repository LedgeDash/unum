# This function is not intended to be invoked directly. Instead it will be
# triggered by an HTTP starter function.
# Before running this sample, please:
# - create a Durable activity function (default name is "Hello")
# - create a Durable HTTP starter function
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt

import logging
import json

import azure.functions as func
import azure.durable_functions as df


def orchestrator_function(context: df.DurableOrchestrationContext):
    data = context.get_input()

    # logging.info(f"Orchestration input data '{data}'.")
    # logging.info(f"Orchestration input data type '{type(data)}'.")

    aggregator_ret = yield context.call_activity('Aggregator', data)
    # logging.info(f"aggregator output data '{aggregator_ret}'.")
    # logging.info(f"aggregator output data type '{type(aggregator_ret)}'.")
    result = yield context.call_activity('HvacController', aggregator_ret)

    return result

main = df.Orchestrator.create(orchestrator_function)