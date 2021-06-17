import subprocess
import json
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

    bucket = event["bucket"]
    prev_state = event["new decoder state"]
    my_interframe_ivf_fn = event["interframe-only ivf file"]
    prev_key = prev_state.split(".")[0]
    prev_key = prev_key.split("-")[0]
    my_key = my_interframe_ivf_fn.split(".")[0]
    my_key = my_key.split("-")[0]

    prev_initial_state = f'{prev_key}-0.state'
    my_raw_video = f'{my_key}.y4m'
    my_new_state = f'{my_key}-1.state'
    my_final_fn = f'{my_key}.ivf'
    my_final_state = f'{my_key}-1.state'

    # download file to local storage
    s3_client.download_file(bucket, prev_state, f"/tmp/{prev_state}")
    s3_client.download_file(bucket, my_interframe_ivf_fn, f"/tmp/{my_interframe_ivf_fn}")
    s3_client.download_file(bucket, prev_initial_state, f"/tmp/{prev_initial_state}")
    s3_client.download_file(bucket, my_raw_video, f"/tmp/{my_raw_video}")

    # rebase: Without recoding any frames, update my interframe-only ivf file's decoder states
    #./xc-enc -W -w 0.75 -i y4m -o 3.ivf -r -I 2-1.state -p 3-1.ivf -S 2-0.state -O 3-1.state 3.y4m
    ret = subprocess.run(["./xc-enc",
        "-W",
        "-w",
        "0.75",
        "-i",
        "y4m",
        "-o",
        f'/tmp/{my_final_fn}',
        "-r",
        "-I",
        f'/tmp/{prev_state}',
        "-p"
        f'/tmp/{my_interframe_ivf_fn}',
        "-S",
        f"/tmp/{prev_initial_state}",
        "-O",
        f'/tmp/{my_final_state}',
        f'/tmp/{my_raw_video}'
        ],
        capture_output=True)

    # upload my final interframe-only ivf file and my final decoder state back to S3
    s3_client.upload_file(f'/tmp/{my_final_fn}', bucket, my_final_fn)
    s3_client.upload_file(f'/tmp/{my_final_state}', bucket, my_final_state)

    if int(my_key) >= 100:
        return

    # check if the next chunk's IVF file exists.
    next_key = int(my_key)+1
    next_ivf = f'{next_key}-1.ivf'

    timeout = 0
    while check_s3_file_exist(bucket, next_ivf) == False:
        time.sleep(1)
        timeout = timeout+1
        if timeout >= 10:
            return

    ret = {"bucket": bucket, "interframe-only ivf file": next_ivf, "new decoder state": my_final_state}

    response = lambda_client.invoke(
        FunctionName='excamera-unum-basic-rebase',
        InvocationType='Event',
        LogType='None',
        Payload=json.dumps(ret),
    )
    ret = response['Payload'].read()
