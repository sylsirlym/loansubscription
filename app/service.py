import os
import json
from .http import HTTP
from dotenv import load_dotenv

load_dotenv()

class Service:
    @staticmethod
    def send_message(msisdn: str, message: str):
        payload = {
            "SenderId": os.getenv("SENDER_ID"),
            "ApiKey": os.getenv("API_KEY"),
            "ClientId": os.getenv("CLIENT_ID"),
            "MessageParameters": [
                {
                    "Number": msisdn,
                    "Text": message
                }
            ]
        }

        headers = {
            'accesskey': os.getenv("ACCESS_KEY"),
            'Content-Type': 'application/json'
        }

        url = os.getenv("SMS_URL")

        result, error = HTTP.send(url, payload, headers)

        if error:
            return {"error": error}
        return result
