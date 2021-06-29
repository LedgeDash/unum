f1-lambda = parallel-pipeline-f1-step-functions
f1-lambda-arn = arn:aws:lambda:us-east-1:746167823857:function:parallel-pipeline-f1-step-functions
lambda-role = arn:aws:iam::746167823857:role/lambda-ex

step-functions-role = arn:aws:iam::746167823857:role/stepfunctions-ex
step-functions-arn-prefix = arn:aws:states:us-east-1:746167823857:stateMachine:parallel-pipeline-depth

MAX_DEPTH := 10
NUMBERS := $(shell seq 1 ${MAX_DEPTH})

f1.zip:
	zip -rj f1.zip ../f1.py ../f1.output

build: f1.zip

.PHONY: create ${CREATE_SF} create-lambda
create-lambda: f1.zip definition.json
	-aws lambda create-function \
	--function-name $(f1-lambda) \
	--zip-file fileb://f1.zip \
	--handler f1.lambda_handler \
	--runtime python3.7 \
	--role $(lambda-role)
	-aws lambda update-function-configuration \
	--function-name $(f1-lambda) \
	--timeout 900

CREATE_SF := $(addprefix create-sf,${NUMBERS})

${CREATE_SF}: create-sf%: ; \
	aws stepfunctions create-state-machine \
	--name parallel-pipeline-depth$* \
	--definition file://definition-depth$*.json \
	--role-arn $(step-functions-role)

create: create-lambda ${CREATE_SF} 


.PHONY: update ${UPDATE_SF} update-lambda
update-lambda: build
	aws lambda update-function-code --function-name $(f1-lambda) --zip-file fileb://f1.zip

UPDATE_SF := $(addprefix update-sf,${NUMBERS})

${UPDATE_SF}: update-sf%: ; \
	aws stepfunctions update-state-machine \
	--state-machine-arn $(addprefix $(step-functions-arn-prefix),$*) \
	--definition file://definition-depth$*.json

update: update-lambda ${UPDATE_SF}

up: build update

test-1:
	aws stepfunctions start-execution \
	--state-machine-arn  $(addprefix $(step-functions-arn-prefix),1) \
	--input file://1-test.json

test-10:
	aws stepfunctions start-execution \
	--state-machine-arn  $(addprefix $(step-functions-arn-prefix),1) \
	--input file://10-test.json

test-100:
	aws stepfunctions start-execution \
	--state-machine-arn  $(addprefix $(step-functions-arn-prefix),1) \
	--input file://100-test.json
test-300:
	aws stepfunctions start-execution \
	--state-machine-arn  $(addprefix $(step-functions-arn-prefix),1) \
	--input file://300-test.json
test-500:
	aws stepfunctions start-execution \
	--state-machine-arn  $(addprefix $(step-functions-arn-prefix),1) \
	--input file://500-test.json
test-700:
	aws stepfunctions start-execution \
	--state-machine-arn  $(addprefix $(step-functions-arn-prefix),1) \
	--input file://700-test.json
test-900:
	aws stepfunctions start-execution \
	--state-machine-arn  $(addprefix $(step-functions-arn-prefix),1) \
	--input file://900-test.json

clean:
	-rm *.zip