# Given the average per-minute power consumption in the last x minutes, decide
# weather to turn HVAC lower.
#
# Output a JSON string of the format {"timestamp": string, "reduce_power": boolean}

from datetime import datetime

THRESHOLD = 1

def handle(event):
	average = event['average_power_consumption']

	command = False

	if average > THRESHOLD:
		command = True

	return {
		"timestamp": datetime.now().isoformat(timespec='milliseconds'),
		"reduce_power": command
	}
