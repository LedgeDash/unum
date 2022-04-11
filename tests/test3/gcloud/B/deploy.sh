gcloud functions deploy unum-test3-B \
--runtime python38 \
--trigger-topic unum-test3-B \
--entry-point lambda_handler \
--env-vars-file env.yaml 