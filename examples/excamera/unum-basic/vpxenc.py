import subprocess
import json
import boto3

s3_client = boto3.client("s3")
lambda_client = boto3.client("lambda")

def lambda_handler(event, context):

    bucket = event['bucket']
    fn = event['file'] # file name should be #.y4m
    key = fn.split('.')[0]
    vpxenc_fn=f'{key}-vpxenc.ivf'
    output_fn=f'{key}-0.ivf'

    # download file to local storage
    s3_client.download_file(bucket, fn, f"/tmp/{fn}")

    # vpxenc
    ret = subprocess.run(["./vpxenc",
        "--ivf",
        "--codec=vp8",
        "--good",
        "--cpu-used=0",
        "--end-usage=cq",
        "--min-q=0",
        "--max-q=63",
        "--cq-level=22",
        "--buf-initial-sz=10000",
        "--buf-optimal-sz=20000",
        "--buf-sz=40000",
        "--undershoot-pct=100",
        "--passes=2",
        "--auto-alt-ref=1",
        "--threads=1",
        "--token-parts=0",
        "--tune=ssim",
        "--target-bitrate=4294967295",
        "-o",
        f'/tmp/{vpxenc_fn}',
        f'/tmp/{fn}'],
        capture_output=True)

    # xc-terminate-chunks
    ret = subprocess.run(["./xc-terminate-chunk",
        f'/tmp/{vpxenc_fn}',
        f'/tmp/{output_fn}'],
        capture_output=True)

    # upload vpx-encoded IVF files back to S3
    s3_client.upload_file(f'/tmp/{output_fn}', bucket, output_fn)


    # if I'm the last iteration, simply return
    if int(key) >= 100:
        return
        
    ret = {"bucket":bucket, "file":output_fn}
    response = lambda_client.invoke(
        FunctionName="excamera-unum-basic-xcdec",
        InvocationType='Event',
        LogType='None',
        Payload=json.dumps(ret),
    )
    ret = response['Payload'].read()
