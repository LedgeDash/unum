
def lambda_handler(event, context):
    if 'bucket' in event:
        # data is from S3. Read text file from S3
        import boto3
        s3_client = boto3.client('s3')
        s3_client.download_file(event['bucket'], event['key'], '/tmp/myfile.txt')

        with open('/tmp/myfile.txt') as f:
            data = f.read()

    else:
        data = event['text']

    return data.upper()