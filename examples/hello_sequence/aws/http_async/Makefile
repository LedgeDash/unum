hello-lambda = hello-http-async
from-lambda = from-http-async
shandong-lambda = shandong-http-async
today-lambda = today-http-async
controller-lambda = hello-seq-http-async
role = arn:aws:iam::908344970015:role/lambda-ex

hello.zip: hello.py
	zip hello.zip hello.py

from.zip: from.py
	zip from.zip from.py

shandong.zip: shandong.py
	zip shandong.zip shandong.py

today.zip: today.py
	zip today.zip today.py

build: hello.zip from.zip shandong.zip today.zip

create: hello.zip from.zip shandong.zip today.zip
	-aws lambda create-function \
	--function-name $(hello-lambda) \
	--zip-file fileb://hello.zip \
	--handler hello.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(from-lambda) \
	--zip-file fileb://from.zip \
	--handler from.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(shandong-lambda) \
	--zip-file fileb://shandong.zip \
	--handler shandong.lambda_handler \
	--runtime python3.7 \
	--role $(role)
	-aws lambda create-function \
	--function-name $(today-lambda) \
	--zip-file fileb://today.zip \
	--handler today.lambda_handler \
	--runtime python3.7 \
	--role $(role)

update: hello.zip from.zip shandong.zip today.zip
	aws lambda update-function-code --function-name $(hello-lambda) --zip-file fileb://hello.zip
	aws lambda update-function-code --function-name $(from-lambda) --zip-file fileb://from.zip
	aws lambda update-function-code --function-name $(shandong-lambda) --zip-file fileb://shandong.zip
	aws lambda update-function-code --function-name $(today-lambda) --zip-file fileb://today.zip

up: build update

test-app:
	aws lambda invoke --function-name $(hello-lambda) out
