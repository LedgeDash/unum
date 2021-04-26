
# Permissions

aggregator-s3 (1st Lambda) needs to have permission to write to S3 via boto3.

hvac_controller-s3 (2nd Lambda) needs to have permission to read from S3 via boto3.

Both are given in the `lambda-ex` role with the "AmazonS3FullAccess" policy.

hvac_controller-s3 (2nd Lambda) needs to give S3 the permission to invoke it.

Use the `aws lambda add-permission` command to add a permission config to the
hvac_controller-s3 function

S3 bucket needs to have event notification to invoke hvac_controller.

Use `aws s3api put-bucket-notification-configuration` command to add such
event notification config. A sample config is in
`intermediary-s3-bucket-event-notification-config.json`.

Note that on the Lambda console, there's an interface to add a "Trigger".
However, there's no equivalent command with the commandline tools. Adding
event notification on the S3 bucket is how you would add a trigger to a Lambda
function. In fact after `aws s3api put-bucket-notification-configuration`,
hvac_controller-s3's console shows S3 as a trigger.
