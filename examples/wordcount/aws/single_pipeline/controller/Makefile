map-lambda = wc-map-controller
reduce-lambda = wc-reduce-controller
controller-lambda = wc-controller
role = arn:aws:iam::908344970015:role/lambda-ex

map.zip: map.py
	zip map.zip map.py

reduce.zip: reduce.py
	zip reduce.zip reduce.py

controller.zip: controller.py
	zip controller.zip controller.py

build: map.zip reduce.zip controller.zip

create: map.zip reduce.zip controller.zip
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
	aws lambda create-function \
	--function-name $(controller-lambda) \
	--zip-file fileb://controller.zip \
	--handler controller.lambda_handler \
	--runtime python3.7 \
	--role $(role)

update: map.zip reduce.zip controller.zip
	aws lambda update-function-code --function-name $(map-lambda) --zip-file fileb://map.zip
	aws lambda update-function-code --function-name $(reduce-lambda) --zip-file fileb://reduce.zip
	aws lambda update-function-code --function-name $(controller-lambda) --zip-file fileb://controller.zip

up: build update

test-app:
	aws lambda invoke --function-name $(controller-lambda) --payload fileb://../book-trimmed.json out
