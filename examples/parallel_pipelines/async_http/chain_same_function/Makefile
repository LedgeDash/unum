unum_map-lambda = parallel-pipeline-unum_map-async-http
fchain-lambda = parallel-pipeline-fchain-async-http


unum_map-lambda-arn = arn:aws:lambda:us-west-1:746167823857:function:parallel-pipeline-unum_map-async-http
fchain-lambda-arn = arn:aws:lambda:us-west-1:746167823857:function:parallel-pipeline-fchain-async-http
lambda-role = arn:aws:iam::746167823857:role/lambda-ex

.PHONY: link unum_map.zip fchain.zip build create update

link:
	-cp ../../f1.py fchain/lambda_handler.py
	-cp ../../f1.output fchain
	-cp ../../../../unum_wrapper.py unum_wrapper.py

unum_map.zip:
	zip -rj unum_map.zip unum_map unum_wrapper.py

fchain.zip:
	zip -rj fchain.zip fchain unum_wrapper.py

build: link fchain.zip unum_map.zip

create: build fchain.zip unum_map.zip
	-aws lambda create-function \
	--function-name $(unum_map-lambda) \
	--zip-file fileb://unum_map.zip \
	--handler unum_wrapper.lambda_handler \
	--runtime python3.7 \
	--role $(lambda-role)
	-aws lambda create-function \
	--function-name $(fchain-lambda) \
	--zip-file fileb://fchain.zip \
	--handler unum_wrapper.lambda_handler \
	--runtime python3.7 \
	--role $(lambda-role)
	-aws lambda update-function-configuration \
	--function-name $(fchain-lambda) \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(unum_map-lambda) \
	--timeout 900


update: build
	aws lambda update-function-code --function-name $(unum_map-lambda) --zip-file fileb://unum_map.zip
	aws lambda update-function-code --function-name $(fchain-lambda) --zip-file fileb://fchain.zip

up: build update

test-small:
	aws lambda invoke --function-name $(unum_map-lambda) \
	--invocation-type Event \
	--payload fileb://small-test.json out
	@cat out
	@printf "\n"

test-1:
	aws lambda invoke --function-name $(unum_map-lambda) \
	--invocation-type Event \
	--payload fileb://1-test.json out
	@cat out
	@printf "\n"

test-100:
	aws lambda invoke --function-name $(unum_map-lambda) \
	--invocation-type Event \
	--payload fileb://100-test.json out
	@cat out
	@printf "\n"
test-300:
	aws lambda invoke --function-name $(unum_map-lambda) \
	--invocation-type Event \
	--payload fileb://300-test.json out
	@cat out
	@printf "\n"
test-500:
	aws lambda invoke --function-name $(unum_map-lambda) \
	--invocation-type Event \
	--payload fileb://500-test.json out
	@cat out
	@printf "\n"
test-700:
	aws lambda invoke --function-name $(unum_map-lambda) \
	--invocation-type Event \
	--payload fileb://700-test.json out
	@cat out
	@printf "\n"
test-900:
	aws lambda invoke --function-name $(unum_map-lambda) \
	--invocation-type Event \
	--payload fileb://900-test.json out
	@cat out
	@printf "\n"

clean:
	-rm *.zip
	rm fchain/lambda_handler.py fchain/f1.output unum_wrapper.py