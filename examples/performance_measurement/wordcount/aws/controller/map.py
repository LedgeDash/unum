import json

def lambda_handler(event, context):
    text = event['data']

    words = text.split()

    ret = [(word, 1) for word in words]

    return ret
