map-lambda = wc-map-http-async
reduce-lambda = wc-reduce-http-async
role = arn:aws:iam::908344970015:role/lambda-ex

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

update: map.zip reduce.zip
	aws lambda update-function-code --function-name $(map-lambda) --zip-file fileb://map.zip
	aws lambda update-function-code --function-name $(reduce-lambda) --zip-file fileb://reduce.zip

up: build update

test-app:
	aws lambda invoke --function-name $(map-lambda) --payload fileb://../book-trimmed.json out
