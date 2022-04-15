gcloud functions deploy unum-test2-B \
--runtime python38 \
--trigger-topic unum-test2-B \
--entry-point lambda_handler \
--env-vars-file env.yaml 