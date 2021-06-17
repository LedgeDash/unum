unum_map_vpxenc-lambda = excamera-unum-basic-unum_map_vpxenc
vpxenc-lambda = excamera-unum-basic-vpxenc
xcdec-lambda = excamera-unum-basic-xcdec
reencode-lambda = excamera-unum-basic-reencode
rebase-lambda = excamera-unum-basic-rebase

unum_map_vpxenc-lambda-arn = arn:aws:lambda:us-west-1:746167823857:function:excamera-unum-basic-unum_map_vpxenc
vpxenc-lambda-arn = arn:aws:lambda:us-west-1:746167823857:function:excamera-unum-basic-vpxenc
xcdec-lambda-arn = arn:aws:lambda:us-west-1:746167823857:function:excamera-unum-basic-xcdec
reencode-lambda-arn = arn:aws:lambda:us-west-1:746167823857:function:excamera-unum-basic-reencode
rebase-lambda-arn = arn:aws:lambda:us-west-1:746167823857:function:excamera-unum-basic-rebase

lambda-role = arn:aws:iam::746167823857:role/lambda-ex

# .PHONY: link unum_map.zip fchain.zip build create update

.PHONY: unum_map_vpxenc.zip vpxenc.zip xcdec.zip reencode.zip rebase.zip build update-lambda update-sf

unum_map_vpxenc.zip:
	zip -j unum_map_vpxenc.zip unum_map_vpxenc.py

vpxenc.zip:
	zip -j vpxenc.zip vpxenc.py ../excamera-static-bins/vpxenc ../excamera-static-bins/xc-terminate-chunk

xcdec.zip:
	zip -j xcdec.zip xcdec.py ../excamera-static-bins/xc-dump

reencode.zip:
	zip -j reencode.zip reencode.py ../excamera-static-bins/xc-enc

rebase.zip:
	zip -j rebase.zip rebase.py ../excamera-static-bins/xc-enc

build: unum_map_vpxenc.zip vpxenc.zip xcdec.zip reencode.zip rebase.zip

create-lambda: build
	-aws lambda create-function \
	--function-name $(unum_map_vpxenc-lambda) \
	--zip-file fileb://unum_map_vpxenc.zip \
	--handler unum_map_vpxenc.lambda_handler \
	--runtime python3.7 \
	--role $(lambda-role)
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
	--function-name $(reencode-lambda) \
	--memory-size 1024 \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(rebase-lambda) \
	--memory-size 1024 \
	--timeout 900
	-aws lambda update-function-configuration \
	--function-name $(unum_map_vpxenc-lambda) \
	--timeout 900

update-lambda: build
	aws lambda update-function-code --function-name $(unum_map_vpxenc-lambda) --zip-file fileb://unum_map_vpxenc.zip
	aws lambda update-function-code --function-name $(vpxenc-lambda) --zip-file fileb://vpxenc.zip
	aws lambda update-function-code --function-name $(xcdec-lambda) --zip-file fileb://xcdec.zip
	aws lambda update-function-code --function-name $(reencode-lambda) --zip-file fileb://reencode.zip
	aws lambda update-function-code --function-name $(rebase-lambda) --zip-file fileb://rebase.zip
	
up: update-lambda

test:
	aws lambda invoke --function-name $(unum_map_vpxenc-lambda) \
	--invocation-type Event \
	--payload fileb://test.json out
	@cat out
	@printf "\n"
test-40:
	aws lambda invoke --function-name $(unum_map_vpxenc-lambda) \
	--invocation-type Event \
	--payload fileb://test-40.json out
	@cat out
	@printf "\n"
	
test-100:
	aws lambda invoke --function-name $(unum_map_vpxenc-lambda) \
	--invocation-type Event \
	--payload fileb://test-100.json out
	@cat out
	@printf "\n"
clean:
	rm *.zip