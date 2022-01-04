def lambda_handler(event, context):
    print(context.__dict__)
    raise
    return event
