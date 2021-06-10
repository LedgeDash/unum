import json

def lambda_handler(event, context):

    ret = []
    for i in range(1,len(event)):
        item = {"bucket": event[i]["bucket"], "prev state": event[i-1]["state"], "ivf file": event[i]["ivf file"]}
        ret.append(item)

    return ret