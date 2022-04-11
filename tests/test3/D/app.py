def lambda_handler(event, context):
    data = event

    return f'B-{data}'
