def lambda_handler(event, context):
    print(event)
    print(context.__dict__)
    raise
    return event
