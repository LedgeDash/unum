aggregator-lambda = aggregator-http-async
hvac_controller-lambda = hvac_controller-http-async
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
