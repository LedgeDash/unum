map-lambda = wc-fixedReducer-singleEmit-map-step-functions
reduce-lambda = wc-fixedReducer-singleEmit-reduce-step-functions
summary-lambda = wc-fixedReducer-singleEmit-summary-step-functions
partition-lambda = wc-fixedReducer-singleEmit-partition-step-functions
map-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:wc-fixedReducer-singleEmit-map-step-functions
reduce-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:wc-fixedReducer-singleEmit-reduce-step-functions
summary-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:wc-fixedReducer-singleEmit-summary-step-functions
partition-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:wc-fixedReducer-singleEmit-partition-step-functions
role = arn:aws:iam::908344970015:role/lambda-ex

intermediary_s3_bucket_arn = arn:aws:s3:::mapreduce-wordcount-fixedreducer-single
intermediary_s3_bucket_name = mapreduce-wordcount-fixedreducer-single
intermediary_s3_owner_account_id = 908344970015

step-functions-arn = arn:aws:states:us-west-1:908344970015:stateMachine:wc-fixedReducer-singleEmit-step-functions

link:
	-ln -sf ../mapper.py mapper.py
	-ln -sf ../user_map.py user_map.py
	-ln -sf ../mapreduce.py mapreduce.py
	-ln -sf ../reducer.py reducer.py
	-ln -sf ../user_reduce.py user_reduce.py
	-ln -sf ../mapreduce.py mapreduce.py
	-ln -sf ../summary.py summary.py
	-ln -sf ../partition.py partition.py

map.zip: mapper.py user_map.py mapreduce.py
	zip map.zip mapper.py user_map.py mapreduce.py

reduce.zip: reducer.py user_reduce.py mapreduce.py
	zip reduce.zip reducer.py user_reduce.py mapreduce.py

summary.zip: summary.py
	zip summary.zip summary.py

partition.zip: partition.py
	zip partition.zip partition.py

build: link map.zip reduce.zip summary.zip partition.zip

create: map.zip reduce.zip summary.zip partition.zip
	-aws lambda create-function \
	--function-name $(map-lambda) \
	--zip-file fileb://map.zip \
	--handler mapper.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(reduce-lambda) \
	--zip-file fileb://reduce.zip \
	--handler reducer.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(partition-lambda) \
	--zip-file fileb://partition.zip \
	--handler partition.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(summary-lambda) \
	--zip-file fileb://summary.zip \
	--handler summary.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda update-function-configuration \
	--function-name $(map-lambda) \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(reduce-lambda) \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(partition-lambda) \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(summary-lambda) \
	--timeout 900

set-time:
	-aws lambda update-function-configuration \
	--function-name $(map-lambda) \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(reduce-lambda) \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(partition-lambda) \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(summary-lambda) \
	--timeout 900

update: build map.zip reduce.zip partition.zip summary.zip definition.json
	aws lambda update-function-code --function-name $(map-lambda) --zip-file fileb://map.zip
	aws lambda update-function-code --function-name $(reduce-lambda) --zip-file fileb://reduce.zip
	aws lambda update-function-code --function-name $(partition-lambda) --zip-file fileb://partition.zip
	aws lambda update-function-code --function-name $(summary-lambda) --zip-file fileb://summary.zip
	aws stepfunctions update-state-machine \
	--state-machine-arn $(step-functions-arn) \
	--definition file://definition.json

up: build update

test-app-small:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://../../../6Jokes-chunks-small.json

test-app-large:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://../../../6Jokes-chunks-large.json

clean:
	-rm *.zip
	rm mapper.py user_map.py mapreduce.py reducer.py user_reduce.py summary.py partition.py