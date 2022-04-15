gcloud functions deploy unum-test2-A \
--runtime python38 \
--trigger-topic unum-test2-A \
--entry-point lambda_handler \
--env-vars-file env.yaml 