upper-lambda = text-fan-in-upper
cat-lambda = text-fan-in-cat

upper-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:text-fan-in-upper
cat-lambda-arm = arn:aws:lambda:us-west-1:908344970015:function:text-fan-in-cat
role = arn:aws:iam::908344970015:role/lambda-ex
step-functions-arn = arn:aws:states:us-west-1:908344970015:stateMachine:Mapstate

upper.zip:
	zip -rj upper.zip ../upper.py
cat.zip:
	zip -rj cat.zip ../cat.py

build: upper.zip cat.zip

create: upper.zip cat.zip
	-aws lambda create-function \
	--function-name $(upper-lambda) \
	--zip-file fileb://upper.zip \
	--handler upper.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(cat-lambda) \
	--zip-file fileb://cat.zip \
	--handler cat.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda update-function-configuration \
	--function-name $(upper-lambda) \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(cat-lambda) \
	--timeout 900

update: build upper.zip cat.zip
	aws lambda update-function-code --function-name $(upper-lambda) --zip-file fileb://upper.zip
	aws lambda update-function-code --function-name $(cat-lambda) --zip-file fileb://cat.zip
	aws stepfunctions update-state-machine \
	--state-machine-arn $(step-functions-arn) \
	--definition file://definition.json

up: build update

test-app-small:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://small-text.json

test-app-large:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://large-text-in-s3.json

clean:
	-rm *.zip