# This function is not intended to be invoked directly. Instead it will be
# triggered by an orchestrator function.
# Before running this sample, please:
# - create a Durable orchestration function
# - create a Durable HTTP starter function
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt

import logging
from datetime import datetime

THRESHOLD = 1

def main(name):

    # logging.info(f"hvac controller input data '{name}'.")
    # logging.info(f"hvac controller input data type '{type(name)}'.")
    
    average = name['average_power_consumption']

    command = 0

    if average > THRESHOLD:
        command = 1

    action = {
        "timestamp": datetime.now().isoformat(timespec='milliseconds'),
        "reduce_power": command
    }

    return action
