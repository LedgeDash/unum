# The function is invoked in an event-driven manner. The input to the function
# is an event, An event is a JSON-formatted document that contains data for a
# Lambda function to process. The Lambda runtime converts the event to an object
# and passes it to your function code. It is usually of the Python dict type. It
# can also be list, str, int, float, or the NoneType type. Such an interface
# resembles that of AWS Lambda
# (https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html).
#
# In the case of this function, the event contains a reference to the image
# file. For example, the reference may be a key in an S3 bucket
# (https://docs.aws.amazon.com/lambda/latest/dg/with-s3-example.html).  The
# function code needs to explicitly read the image via the reference before
# processing.



def handle(event):
    fname = event['filename']
    return
