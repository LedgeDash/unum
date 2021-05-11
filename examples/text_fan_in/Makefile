upper-lambda = text-fan-in-upper
cat-lambda = text-fan-in-cat

upper-lambda-arn = 
cat-lambda-arm = 
role = arn:aws:iam::908344970015:role/lambda-ex

upper.zip: upper
	zip -rj upper.zip ../upper.py
cat.zip: cat
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

clean:
	-rm *.zip
	-rm mapper/lambda_handler.py mapper/user_map.py mapper/mapreduce.py \
	reducer/lambda_handler.py reducer/user_reduce.py reducer/mapreduce.py \
	summary/lambda_handler.py \
	partition/lambda_handler.py \
	unum_wrapper.py