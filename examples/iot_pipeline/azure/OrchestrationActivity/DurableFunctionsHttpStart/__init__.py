# This function an HTTP starter function for Durable Functions.
# Before running this sample, please:
# - create a Durable orchestration function
# - create a Durable activity function (default name is "Hello")
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt
 
import logging

import azure.functions as func
import azure.durable_functions as df


async def main(req: func.HttpRequest, starter: str) -> func.HttpResponse:

    data = [{"2021-02-20T08:30:00.000":120}, {"2021-02-20T09:30:00.000":25.0}, {"2021-02-20T10:30:00.000":211.2}, {"2021-02-20T11:30:00.000":10}]
    client = df.DurableOrchestrationClient(starter)
    instance_id = await client.start_new(req.route_params["functionName"], None, data)

    logging.info(f"Started orchestration with ID = '{instance_id}'.")

    return client.create_check_status_response(req, instance_id)