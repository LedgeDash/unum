def lambda_handler(event, context):
    with open('f3.output') as f:
        ret = f.read()
    return ret 
