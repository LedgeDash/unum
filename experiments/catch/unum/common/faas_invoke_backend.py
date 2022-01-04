import boto3
import json

class InvocationBackend(object):
    subclasses = {}

    @classmethod
    def add_backend(cls, platform):
        def wrapper(subclass):
            cls.subclasses[platform] = subclass
            return subclass

        return wrapper

    @classmethod
    def create(cls, platform):
        if platform not in cls.subclasses:
            raise ValueError(f'unum does not support {platform}')

        return cls.subclasses[platform]()



@InvocationBackend.add_backend('aws')
class AWSLambdaBackend(InvocationBackend):

    def __init__(self):
        self.lambda_client = boto3.client("lambda")

    def invoke(self, function, data):
        return self._http_invoke_async(function, data)

    def _http_invoke_async(self, function, data):
        '''
        @param function string function arn
        @param data dict
        '''
        response = self.lambda_client.invoke(
            FunctionName=function,
            InvocationType='Event',
            LogType='None',
            Payload=json.dumps(data),
        )
        ret = response['Payload'].read()

        return


@InvocationBackend.add_backend('fake')
class FakeFaaSBackend(InvocationBackend):

    def invoke(self, function, data):
        print(f'[FaaS Backend: fake] Invoking {function}')
        print(f'[FaaS Backend: fake] Payload: {data}')
        return data