def lambda_handler(event, context):
    with open('f2.output') as f:
        ret = f.read()
    return ret 
