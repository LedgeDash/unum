gcloud functions deploy unum-test3-D \
--runtime python38 \
--trigger-topic unum-test3-D \
--entry-point lambda_handler \
--env-vars-file env.yaml 