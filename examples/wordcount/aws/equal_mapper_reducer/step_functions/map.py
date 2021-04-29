import json

def lambda_handler(event, context):
    text = event

    words = text.split()

    ret = [(word, 1) for word in words]

    return ret
