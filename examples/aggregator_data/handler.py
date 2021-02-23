# Calculating the total and average of power consumption in the last X hours.
#
# Expected input is a JSON list of {timestamp:
# power_delta_from_last_tsp}, because the sensor has limited memory.
#
# The list can be of varying length. It's up to the sensor how frequently it
# invokes this function.
# The timestamp delta (i.e., precision) is also decided by the sensor.
#
# Output: A JSON string {starting_tsp, ending_tsp, average, total}
import json
from datetime import date

def handle(event):
    data = json.loads(event)
    series = data['data']
    num_tsp = len(series)

    return series
