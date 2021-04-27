import json

def handle(data):

    words = data.split()

    ret = [(word, 1) for word in words]

    return ret
