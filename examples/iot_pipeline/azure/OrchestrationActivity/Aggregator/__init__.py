# This function is not intended to be invoked directly. Instead it will be
# triggered by an orchestrator function.
# Before running this sample, please:
# - create a Durable orchestration function
# - create a Durable HTTP starter function
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt

import logging
from datetime import datetime
from functools import reduce

def to_datetime(elem):
	if len(elem) != 1:
		raise

	time_str = list(elem)[0]
	time = datetime.fromisoformat(time_str)

	return (time, elem[time_str])

def main(name):
    # logging.info(f"aggregator input data '{name}'.")
    # logging.info(f"aggregator input data type '{type(name)}'.")

    series = name
    num_elem = len(series)

    series = [to_datetime(elem) for elem in series]

    delta = (series[1][0] - series[0][0]).total_seconds()/60 # difference between 2 timestamps in minutes

    total_time_in_mins = delta*num_elem
    total_power_consumption = reduce(lambda x, y: x+y[1], series, 0)

    average_power_consumption = total_power_consumption/total_time_in_mins

    return {
        "starting_tsp": datetime.isoformat(series[0][0]),
        "ending_tsp": datetime.isoformat(series[-1][0]),
        "total_time": total_time_in_mins,
        "total_power_consumption": total_power_consumption,
        "average_power_consumption": average_power_consumption
    }

    # return f"Hello {name}!"
