# Given the average per-minute power consumption in the last x minutes, decide
# weather to turn HVAC lower.
#
# Output a JSON string of the format {"timestamp": string, "reduce_power": boolean}

from datetime import datetime

THRESHOLD = 1

def handle(event):
	average = event['average_power_consumption']

	command = 0

	if average > THRESHOLD:
		command = 1

	return {
		"timestamp": datetime.now().isoformat(timespec='milliseconds'),
		"reduce_power": command
	}
