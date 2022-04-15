gcloud functions deploy unum-test2-C \
--runtime python38 \
--trigger-topic unum-test2-C \
--entry-point lambda_handler \
--env-vars-file env.yaml 