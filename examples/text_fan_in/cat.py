
def lambda_handler(event, context):
    ret = ""
    for d in event:
        ret = ret+d

    # raise IOError(f'{ret}')
    return ret