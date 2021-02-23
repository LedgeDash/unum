# Calculating the total and average of power consumption in the last X hours.
#
# Expected input is a JSON list of {timestamp: power_delta_from_last_tsp},
# because the sensor has limited memory.
#
# The list can be of varying length. It's up to the sensor how frequently it
# invokes this function. The timestamp delta (i.e., precision) is also decided
# by the sensor.
#
# Output: A JSON string {starting_tsp, ending_tsp, total_time, average, total}
# total_time is in mins
# Average is per minute

import json
from datetime import date
from functools import reduce

def to_datetime(elem):
	if len(elem) != 1:
		raise

	time_str = list(elem)[0]
	# time = date.fromisoformat(time_str)
	time = time_str

	return (time, elem[time_str])

def handle(event):
    data = json.loads(event)
    series = data['data']
    num_elem = len(series)

    series = [to_datetime(elem) for elem in series]

    # delta = series[1][0] - series[0][0]
    delta = 60
    total_time_in_mins = delta*num_elem
    total_power_consumption = reduce(lambda x, y: x+y[1], series, 0)

    average_power_consumption = total_power_consumption/total_time_in_mins

    return {
    	"starting_tsp":series[0][0],
    	"ending_tsp": series[-1][0],
    	"total_time": total_time_in_mins,
    	"total_power_consumption": total_power_consumption,
    	"average_power_consumption": average_power_consumption
    }
