unummap-lambda = wc-fixedReducer-singleEmit-unummap-http-async-s3
map-lambda = wc-fixedReducer-singleEmit-map-http-async-s3
reduce-lambda = wc-fixedReducer-singleEmit-reduce-http-async-s3
summary-lambda = wc-fixedReducer-singleEmit-summary-http-async-s3
partition-lambda = wc-fixedReducer-singleEmit-partition-http-async-s3
unummap-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:wc-fixedReducer-singleEmit-unummap-http-async-s3
map-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:wc-fixedReducer-singleEmit-map-http-async-s3
reduce-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:wc-fixedReducer-singleEmit-reduce-http-async-s3
summary-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:wc-fixedReducer-singleEmit-summary-http-async-s3
partition-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:wc-fixedReducer-singleEmit-partition-http-async-s3
role = arn:aws:iam::908344970015:role/lambda-ex

link:
	-cp ../mapper.py mapper/lambda_handler.py
	-cp ../user_map.py mapper/user_map.py
	-cp ../mapreduce.py mapper/mapreduce.py
	-cp ../reducer.py reducer/lambda_handler.py
	-cp ../user_reduce.py reducer/user_reduce.py
	-cp ../mapreduce.py reducer/mapreduce.py
	-cp ../summary.py summary/lambda_handler.py
	-cp ../partition.py partition/lambda_handler.py

unummap.zip: unum_map
	zip -rj unummap.zip unum_wrapper.py unum_map

map.zip: mapper
	zip -rj map.zip unum_wrapper.py mapper

reduce.zip: reducer
	zip -rj reduce.zip unum_wrapper.py reducer

summary.zip: summary
	zip -rj summary.zip unum_wrapper.py summary

partition.zip: partition
	zip -rj partition.zip unum_wrapper.py partition

build: link unummap.zip map.zip reduce.zip summary.zip partition.zip

create: map.zip reduce.zip summary.zip partition.zip unummap.zip
	-aws lambda create-function \
	--function-name $(unummap-lambda) \
	--zip-file fileb://unummap.zip \
	--handler unum_wrapper.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(map-lambda) \
	--zip-file fileb://map.zip \
	--handler unum_wrapper.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(reduce-lambda) \
	--zip-file fileb://reduce.zip \
	--handler unum_wrapper.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(partition-lambda) \
	--zip-file fileb://partition.zip \
	--handler unum_wrapper.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(summary-lambda) \
	--zip-file fileb://summary.zip \
	--handler unum_wrapper.lambda_handler \
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
	-aws lambda update-function-configuration \
	--function-name $(unummap-lambda) \
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
	-aws lambda update-function-configuration \
	--function-name $(unummap-lambda) \
	--timeout 900

update: clean build map.zip reduce.zip partition.zip summary.zip unummap.zip
	aws lambda update-function-code --function-name $(unummap-lambda) --zip-file fileb://unummap.zip
	aws lambda update-function-code --function-name $(map-lambda) --zip-file fileb://map.zip
	aws lambda update-function-code --function-name $(reduce-lambda) --zip-file fileb://reduce.zip
	aws lambda update-function-code --function-name $(partition-lambda) --zip-file fileb://partition.zip
	aws lambda update-function-code --function-name $(summary-lambda) --zip-file fileb://summary.zip

up: build update

test-app-small:
	aws lambda invoke --function-name $(unummap-lambda) \
	--invocation-type Event \
	--payload fileb://../../../6Jokes-chunks-small.json out
	@cat out
	@printf "\n"

test-app-large:
	aws lambda invoke --function-name $(unummap-lambda) --payload fileb://../../../6Jokes-chunks-large.json out
	@cat out
	@printf "\n"

test-partition:
	aws lambda invoke --function-name $(partition-lambda) --payload fileb://partition-input.json out
	@cat out
	@printf "\n"

clean:
	-rm *.zip
	-rm mapper/lambda_handler.py mapper/user_map.py mapper/mapreduce.py \
	reducer/lambda_handler.py reducer/user_reduce.py reducer/mapreduce.py \
	summary/lambda_handler.py \
	partition/lambda_handler.py