map-lambda = wc-map-step-functions
reduce-lambda = wc-reduce-step-functions
role = arn:aws:iam::908344970015:role/lambda-ex
step-functions-arn = arn:aws:states:us-west-1:908344970015:stateMachine:2-stageMapReduceWordCount

map.zip: map.py
	zip map.zip map.py

reduce.zip: reduce.py
	zip reduce.zip reduce.py

build: map.zip reduce.zip

create: map.zip reduce.zip
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

update: map.zip reduce.zip controller.zip
	aws lambda update-function-code --function-name $(map-lambda) --zip-file fileb://map.zip
	aws lambda update-function-code --function-name $(reduce-lambda) --zip-file fileb://reduce.zip

up: build update

test-app-trimmed:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://../book-trimmed.json

test-app:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://../book.json

test-app-large:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://../world.json