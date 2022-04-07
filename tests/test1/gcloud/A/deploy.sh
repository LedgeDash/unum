#
gcloud functions deploy unum-test1-A \
--runtime python38 \
--trigger-topic unum-test1-A \
--entry-point lambda_handler \
--env-vars-file env.yaml 