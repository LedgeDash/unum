aggregator-lambda = aggregator-s3
hvac_controller-lambda = hvac_controller-s3
role = arn:aws:iam::908344970015:role/lambda-ex
intermediary_s3_bucket_arn = arn:aws:s3:::iot-pipeline-intermediary
intermediary_s3_bucket_name = iot-pipeline-intermediary
intermediary_s3_owner_account_id = 908344970015
intermediary_s3_bucket_event_notification_config = s3-event-notification-config.json


aggregator.zip: aggregator.py
	zip aggregator.zip aggregator.py

hvac_controller.zip: hvac_controller.py
	zip hvac_controller.zip hvac_controller.py

build: aggregator.zip hvac_controller.zip

create: aggregator.py hvac_controller.py
	aws lambda create-function --function-name $(aggregator-lambda) \
	--zip-file fileb://aggregator.zip \
	--handler aggregator.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	aws lambda create-function \
	--function-name $(hvac_controller-lambda) \
	--zip-file fileb://hvac_controller.zip \
	--handler hvac_controller.lambda_handler \
	--runtime python3.7 \
	--role $(role)

update: aggregator.py hvac_controller.py
	aws lambda update-function-code --function-name $(aggregator-lambda) --zip-file fileb://aggregator.zip
	aws lambda update-function-code --function-name $(hvac_controller-lambda) --zip-file fileb://hvac_controller.zip

up: build update

add-s3-invoke-permission:
	aws lambda add-permission --function-name $(hvac_controller-lambda) \
	--principal s3.amazonaws.com \
	--statement-id s3invoke \
	--action "lambda:InvokeFunction" \
	--source-arn $(intermediary_s3_bucket_arn) \
	--source-account $(intermediary_s3_owner_account_id)

add-s3-event-notification:
	aws s3api put-bucket-notification-configuration \
	--bucket $(intermediary_s3_bucket_name) \
	--notification-configuration file://$(intermediary_s3_bucket_event_notification_config)

test-aggregator:
	aws lambda invoke --function-name $(aggregator-lambda) --payload fileb://../power_consumption_data.json out
	@cat out
	@printf "\n"

test-hvac:
	aws lambda invoke --function-name $(hvac_controller-lambda) --payload fileb://sample-s3-event.json out
	@cat out
	@printf "\n"

test-hvac-s3:
	aws s3 cp ../aggregator_output.json s3://iot-pipeline-intermediary/test.json
	@printf "\n"

test-app:
	aws lambda invoke --function-name $(aggregator-lambda) --invocation-type Event --payload fileb://../power_consumption_data.json out
