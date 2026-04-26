

import boto3

class AwsSecretHelper:
    def __init__(self):
        self.ClientSecrets = boto3.client("secretsmanager",region_name="ap-south-1")

    def get_Secret(self,secret):
        try:
            response = self.ClientSecrets.get_secret_value(SecretId = secret)
            return response["SecretString"]
        except Exception as e:
            print(f"Error While retreving secret: {str(e)}")
            raise e
