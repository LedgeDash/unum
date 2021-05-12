f1-lambda = parallel-pipeline-f1
f2-lambda = parallel-pipeline-f2
f3-lambda = parallel-pipeline-f3

f1-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:parallel-pipeline-f1
f2-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:parallel-pipeline-f2
f3-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:parallel-pipeline-f3
role = arn:aws:iam::908344970015:role/lambda-ex

step-functions-arn = arn:aws:states:us-west-1:908344970015:stateMachine:artificial-parallel-pipeline

f1.zip:
	zip -rj f1.zip ../f1.py ../f1.output

f2.zip:
	zip -rj f2.zip ../f2.py ../f2.output

f3.zip:
	zip -rj f3.zip ../f3.py ../f3.output

build: f1.zip f2.zip f3.zip

create: f1.zip f2.zip f3.zip
	-aws lambda create-function \
	--function-name $(f1-lambda) \
	--zip-file fileb://f1.zip \
	--handler f1.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(f2-lambda) \
	--zip-file fileb://f2.zip \
	--handler f2.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(f3-lambda) \
	--zip-file fileb://f3.zip \
	--handler f3.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda update-function-configuration \
	--function-name $(f1-lambda) \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(f2-lambda) \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(f3-lambda) \
	--timeout 900


update: build f1.zip f2.zip f3.zip
	aws lambda update-function-code --function-name $(f1-lambda) --zip-file fileb://f1.zip
	aws lambda update-function-code --function-name $(f2-lambda) --zip-file fileb://f2.zip
	aws lambda update-function-code --function-name $(f3-lambda) --zip-file fileb://f3.zip
	aws stepfunctions update-state-machine \
	--state-machine-arn $(step-functions-arn) \
	--definition file://definition.json

up: build update

test-small:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://small-test.json

test-100:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://100-test.json
test-300:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://300-test.json
test-500:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://500-test.json
test-700:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://700-test.json
test-900:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://900-test.json

clean:
	-rm *.zip