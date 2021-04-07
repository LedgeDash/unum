aggregator-lambda = aggregator-sns
hvac_controller-lambda = hvac_controller-sns
hvac_controller-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:hvac_controller-sns
role = arn:aws:iam::908344970015:role/lambda-ex
intermediary_sns_topic_arn = arn:aws:sns:us-west-1:908344970015:iot-pipeline-intermediary-topic
intermediary_sns_topic_name = iot-pipeline-intermediary-topic
intermediary_sns_topic_owner_account_id = 908344970015
hvac_controller-lambda-sns-subscription-arn = arn:aws:sns:us-west-1:908344970015:iot-pipeline-intermediary-topic:32c6eba8-8d21-4cd2-bb6a-8182b06e2b9e



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

create-sns-topic:
	aws sns create-topic \
	--name $(intermediary_sns_topic_name) \

subscribe-callee-lambda-to-sns:
	aws sns subscribe --protocol lambda \
	--topic-arn $(intermediary_sns_topic_arn) \
	--notification-endpoint $(hvac_controller-lambda-arn) \

add-sns-invoke-permission:
	aws lambda add-permission \
	--function-name $(hvac_controller-lambda) \
	--principal sns.amazonaws.com \
	--statement-id snsinvoke \
	--action "lambda:InvokeFunction" \
	--source-arn $(intermediary_sns_topic_arn)

test-aggregator:
	aws lambda invoke --function-name $(aggregator-lambda) --payload fileb://../power_consumption_data.json out
	@cat out
	@printf "\n"

test-hvac:
	aws sns publish \
	--message file://../aggregator_output.json \
	--subject Test \
	--topic-arn $(intermediary_sns_topic_arn)
	@printf "\n"

test-app:
	aws lambda invoke --function-name $(aggregator-lambda) --invocation-type Event --payload fileb://../power_consumption_data.json out
