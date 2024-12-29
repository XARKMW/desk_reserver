import boto3
from botocore.exceptions import ClientError

class SecureCredentialHandler:
    def __init__(self):
        self.ssm = boto3.client('ssm')

    def load_credentials(self):
        """Load credentials from AWS SSM Parameter Store"""
        try:
            params = {
                'BOOKING_USERNAME': self.ssm.get_parameter(
                    Name='/desk_booking/username',
                    WithDecryption=True
                )['Parameter']['Value'],
                'BOOKING_PASSWORD': self.ssm.get_parameter(
                    Name='/desk_booking/password',
                    WithDecryption=True
                )['Parameter']['Value'],
                'BOOKING_URL': "https://engage.spaceiq.com/floor/1667/desks/16193"
            }
            return params
        except ClientError as e:
            raise Exception(f"Failed to load credentials from SSM: {str(e)}")