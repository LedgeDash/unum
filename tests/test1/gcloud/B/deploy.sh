#
gcloud functions deploy unum-test1-B \
--runtime python38 \
--trigger-topic unum-test1-B \
--entry-point lambda_handler \
--env-vars-file env.yaml 