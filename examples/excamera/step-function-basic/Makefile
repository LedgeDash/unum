vpxenc-lambda = excamera-stepfunction-basic-vpxenc
xcdec-lambda = excamera-stepfunction-basic-xcdec
reencode-lambda = excamera-stepfunction-basic-reencode
group-lambda = excamera-stepfunction-basic-group
rebase-lambda = excamera-stepfunction-basic-rebase


vpxenc-lambda-arn = arn:aws:lambda:us-west-1:746167823857:function:excamera-stepfunction-basic-vpxenc
xcdec-lambda-arn = arn:aws:lambda:us-west-1:746167823857:function:excamera-stepfunction-basic-xcdec
reencode-lambda-arn = arn:aws:lambda:us-west-1:746167823857:function:excamera-stepfunction-basic-reencode
group-lambda-arn = arn:aws:lambda:us-west-1:746167823857:function:excamera-stepfunction-basic-group
rebase-lambda-arn = arn:aws:lambda:us-west-1:746167823857:function:excamera-stepfunction-basic-rebase

step-functions-arn = arn:aws:states:us-west-1:746167823857:stateMachine:excamera-sf-basic

lambda-role = arn:aws:iam::746167823857:role/lambda-ex

# .PHONY: link unum_map.zip fchain.zip build create update

.PHONY: vpxenc.zip xcdec.zip group.zip reencode.zip rebase.zip build update-lambda update-sf

vpxenc.zip:
	zip -j vpxenc.zip vpxenc.py ../excamera-static-bins/vpxenc ../excamera-static-bins/xc-terminate-chunk

xcdec.zip:
	zip -j xcdec.zip xcdec.py ../excamera-static-bins/xc-dump

group.zip:
	zip -j group.zip group.py

reencode.zip:
	zip -j reencode.zip reencode.py ../excamera-static-bins/xc-enc

rebase.zip:
	zip -j rebase.zip rebase.py ../excamera-static-bins/xc-enc

build: vpxenc.zip xcdec.zip group.zip reencode.zip rebase.zip

create-lambda: build
	-aws lambda create-function \
	--function-name $(vpxenc-lambda) \
	--zip-file fileb://vpxenc.zip \
	--handler vpxenc.lambda_handler \
	--runtime python3.7 \
	--role $(lambda-role)
	-aws lambda create-function \
	--function-name $(xcdec-lambda) \
	--zip-file fileb://xcdec.zip \
	--handler xcdec.lambda_handler \
	--runtime python3.7 \
	--role $(lambda-role)
	-aws lambda create-function \
	--function-name $(group-lambda) \
	--zip-file fileb://group.zip \
	--handler group.lambda_handler \
	--runtime python3.7 \
	--role $(lambda-role)
	-aws lambda create-function \
	--function-name $(reencode-lambda) \
	--zip-file fileb://reencode.zip \
	--handler reencode.lambda_handler \
	--runtime python3.7 \
	--role $(lambda-role)
	-aws lambda create-function \
	--function-name $(rebase-lambda) \
	--zip-file fileb://rebase.zip \
	--handler rebase.lambda_handler \
	--runtime python3.7 \
	--role $(lambda-role)
	-aws lambda update-function-configuration \
	--function-name $(vpxenc-lambda) \
	--memory-size 1024 \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(xcdec-lambda) \
	--memory-size 1024 \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(group-lambda) \
	--memory-size 1024 \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(reencode-lambda) \
	--memory-size 1024 \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(rebase-lambda) \
	--memory-size 1024 \
	--timeout 900

update-lambda: build
	aws lambda update-function-code --function-name $(vpxenc-lambda) --zip-file fileb://vpxenc.zip
	aws lambda update-function-code --function-name $(xcdec-lambda) --zip-file fileb://xcdec.zip
	aws lambda update-function-code --function-name $(group-lambda) --zip-file fileb://group.zip
	aws lambda update-function-code --function-name $(reencode-lambda) --zip-file fileb://reencode.zip
	aws lambda update-function-code --function-name $(rebase-lambda) --zip-file fileb://rebase.zip
	
update-sf: definition.json
	aws stepfunctions update-state-machine \
	--state-machine-arn $(step-functions-arn) \
	--definition file://definition.json

up: update-lambda update-sf

test:
	aws stepfunctions start-execution \
	--state-machine-arn  $(step-functions-arn) \
	--input file://test.json

clean:
	rm *.zip