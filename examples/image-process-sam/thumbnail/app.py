from PIL import Image

import boto3

s3_client = boto3.client("s3")

def lambda_handler(event, context):
    if "resources" in event:
        # triggered by an S3 event
        pass
    else:
        # raise IOError(f'{event}')
        bucket = event['bucket']
        key = event['key']

    s3_client.download_file(bucket, key, f"/tmp/{key}")

    im = Image.open(f"/tmp/{key}")

    out = im.resize((512, 512))
    out.save(f'/tmp/{key}-resized.jpg', "JPEG")

    s3_client.upload_file(f'/tmp/{key}-resized.jpg',bucket, f'{key}-resized.jpg')

    return {"bucket": bucket, "key": f'{key}-resized.jpg'}
