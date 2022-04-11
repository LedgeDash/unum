gcloud functions deploy unum-test3-C \
--runtime python38 \
--trigger-topic unum-test3-C \
--entry-point lambda_handler \
--env-vars-file env.yaml 