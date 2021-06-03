import torch
import torchvision
import base64
import json

from PIL import Image
from io import BytesIO
from facenet_pytorch import MTCNN, InceptionResnetV1
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

    im = im.resize((160,160))

    mtcnn = MTCNN(image_size=160, margin=0)
    x, prob = mtcnn(im, return_prob = True)
    ret = {"prob":str(prob)}

    output_fn = f'{key}-face-presence.json'
    with open(f'/tmp/{output_fn}', 'w') as f:
        f.write(json.dumps(ret))

    s3_client.upload_file(f'/tmp/{output_fn}' ,bucket, output_fn)

    return {"prob":str(prob)}
