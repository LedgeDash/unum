import subprocess
import json, time
import boto3

s3_client = boto3.client("s3")
lambda_client = boto3.client("lambda")

def check_s3_file_exist(bucket, key):
    response = s3_client.head_object(
        Bucket=bucket,
        Key=key
    )

    if "LastModified" in response:
        return True
    return False


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


    # check if the next chunk's IVF file exists.
    next_key = int(key)+1
    next_ivf = f'{next_key}-0.ivf'

    timeout = 0
    while check_s3_file_exist(bucket, next_ivf) == False:
        time.sleep(1)
        timeout = timeout+1
        if timeout >= 10:
            return

    ret = {"bucket": bucket, "ivf file": next_ivf, "prev state": output_fn}

    response = lambda_client.invoke(
        FunctionName="excamera-unum-basic-reencode",
        InvocationType='Event',
        LogType='None',
        Payload=json.dumps(ret),
    )
    ret = response['Payload'].read()
