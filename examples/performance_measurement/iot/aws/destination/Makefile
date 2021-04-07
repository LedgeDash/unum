aggregator-lambda = aggregator-destination
hvac_controller-lambda = hvac_controller-destination
role = arn:aws:iam::908344970015:role/lambda-ex

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

generate-destination:
	echo "{\"OnSuccess\": {\"Destination\": \"`aws lambda get-function --function-name hvac_controller-destination | grep FunctionArn | cut -d '"' -f 4`\"} }" > aggregator_destination_config.json

#set-destination: generate-destination
#	aws lambda put-function-event-invoke-config --function-name aggregator-destination --destination-config fileb://aggregator_destination_config.json

clear-destination: 
	aws lambda delete-function-event-invoke-config --function-name $(aggregator-lambda)

test-aggregator:
	aws lambda invoke --function-name $(aggregator-lambda) --payload fileb://../power_consumption_data.json out
	@cat out
	@printf "\n"

test-hvac:
	aws lambda invoke --function-name $(hvac_controller-lambda) --payload fileb://../aggregator_output.json out
	@cat out
	@printf "\n"

test-app:
	aws lambda invoke --function-name $(aggregator-lambda) --invocation-type Event --payload fileb://../power_consumption_data.json out
