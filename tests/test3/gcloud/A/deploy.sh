gcloud functions deploy unum-test3-A \
--runtime python38 \
--trigger-topic unum-test3-A \
--entry-point lambda_handler \
--env-vars-file env.yaml 