import subprocess
import json
import boto3

s3_client = boto3.client("s3")

def lambda_handler(event, context):
    bucket = event['bucket']
    fn = event['file'] # file name should be #.y4m
    key = fn.split('.')[0]
    key = key.split('-')[0]
    output_fn=f'{key}-0.state'

     # download file to local storage
    s3_client.download_file(bucket, fn, f"/tmp/{fn}")

    # xc-dump
    ret = subprocess.run(["./xc-dump",
        f'/tmp/{fn}',
        f'/tmp/{output_fn}'],
        capture_output=True)

    # upload decoder state file back to S3
    s3_client.upload_file(f'/tmp/{output_fn}', bucket, output_fn)

    return {"bucket": bucket, "ivf file": fn, "state": output_fn}