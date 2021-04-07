
# Permissions

aggregator-sns (1st Lambda) needs to have permission to write to sns via
boto3.

hvac_controller-sns (2nd Lambda) needs to have permission to read from sns via
boto3.

Both are given in the `lambda-ex` role with the "AmazonSNSFullAccess " policy.

hvac_controller-sns (2nd Lambda) needs to give sns the permission to invoke
it.

Use the `aws lambda add-permission` command to add a permission config to the
hvac_controller-sns function. See `make add-sns-invoke-permission`.

After add the permission, the Lambda console will show SNS as a trigger for
hvac_controller-sns. However, until we subscribe hvac_controller-sns to the
sns topic, publishing messages to the SNS topic will NOT invoke
hvac_controller-sns.

The intermediary sns topic needs to have event notification to invoke
hvac_controller-sns. This is done by subscribing the hvac_controller-sns
function onto the sns topic. We can do this with `aws sns subscribe`. See
`make subscribe-callee-lambda-to-sns` for an example.

SNS invokes functions asynchronously with an event that contains a message and
metadata.