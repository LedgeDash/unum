map-lambda = wc-equalMR-map-step-functions
reduce-lambda = wc-equalMR-reduce-step-functions
summary-lambda = wc-equalMR-summary-step-functions
role = arn:aws:iam::908344970015:role/lambda-ex
step-functions-arn = arn:aws:states:us-west-1:908344970015:stateMachine:MapReduceWC2

map.zip: map.py
	zip map.zip map.py

reduce.zip: reduce.py
	zip reduce.zip reduce.py

summary.zip: summary.py
	zip summary.zip summary.py

build: map.zip reduce.zip summary.zip

create: map.zip reduce.zip summary.zip
	-aws lambda create-function \
	--function-name $(map-lambda) \
	--zip-file fileb://map.zip \
	--handler map.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(reduce-lambda) \
	--zip-file fileb://reduce.zip \
	--handler reduce.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(summary-lambda) \
	--zip-file fileb://summary.zip \
	--handler summary.lambda_handler \
	--runtime python3.7 \
	--role $(role)

update: map.zip reduce.zip summary.zip definition.json
	aws lambda update-function-code --function-name $(map-lambda) --zip-file fileb://map.zip
	aws lambda update-function-code --function-name $(reduce-lambda) --zip-file fileb://reduce.zip
	aws lambda update-function-code --function-name $(summary-lambda) --zip-file fileb://summary.zip
	aws stepfunctions update-state-machine \
	--state-machine-arn $(step-functions-arn) \
	--definition file://definition.json

up: build update

test-app:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://../../../6Jokes-chunks.json
