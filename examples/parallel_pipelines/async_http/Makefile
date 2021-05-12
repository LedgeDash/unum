unum_map-lambda = parallel-pipeline-unum_map-async-http
f1-lambda = parallel-pipeline-f1-async-http
f2-lambda = parallel-pipeline-f2-async-http
f3-lambda = parallel-pipeline-f3-async-http

unum_map-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:parallel-pipeline-unum_map-async-http
f1-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:parallel-pipeline-f1-async-http
f2-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:parallel-pipeline-f2-async-http
f3-lambda-arn = arn:aws:lambda:us-west-1:908344970015:function:parallel-pipeline-f3-async-http
role = arn:aws:iam::908344970015:role/lambda-ex

link:
	-cp ../f1.py f1/lambda_handler.py
	-cp ../f2.py f2/lambda_handler.py
	-cp ../f3.py f3/lambda_handler.py
	-cp ../../../unum_wrapper.py unum_wrapper.py

unum_map.zip:
	zip -rj unum_map.zip unum_map unum_wrapper.py

f1.zip:
	zip -rj f1.zip f1 ../f1.output unum_wrapper.py

f2.zip:
	zip -rj f2.zip f2 ../f2.output unum_wrapper.py

f3.zip:
	zip -rj f3.zip f3 ../f3.output unum_wrapper.py

build: link f1.zip f2.zip f3.zip unum_map.zip

create: f1.zip f2.zip f3.zip unum_map.zip
	-aws lambda create-function \
	--function-name $(unum_map-lambda) \
	--zip-file fileb://unum_map.zip \
	--handler unum_wrapper.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(f1-lambda) \
	--zip-file fileb://f1.zip \
	--handler unum_wrapper.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(f2-lambda) \
	--zip-file fileb://f2.zip \
	--handler unum_wrapper.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(f3-lambda) \
	--zip-file fileb://f3.zip \
	--handler unum_wrapper.lambda_handler \
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
	-aws lambda update-function-configuration \
	--function-name $(unum_map-lambda) \
	--timeout 900


update: build f1.zip f2.zip f3.zip unum_map.zip
	aws lambda update-function-code --function-name $(unum_map-lambda) --zip-file fileb://unum_map.zip
	aws lambda update-function-code --function-name $(f1-lambda) --zip-file fileb://f1.zip
	aws lambda update-function-code --function-name $(f2-lambda) --zip-file fileb://f2.zip
	aws lambda update-function-code --function-name $(f3-lambda) --zip-file fileb://f3.zip

up: build update

test-small:
	aws lambda invoke --function-name $(unum_map-lambda) \
	--invocation-type Event \
	--payload fileb://small-test.json out
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
	rm f1/lambda_handler.py f2/lambda_handler.py f3/lambda_handler.py unum_wrapper.py