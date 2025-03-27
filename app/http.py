import os
import requests
import traceback
import logging
# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class HTTP:
    @staticmethod
    def send(url, payload, headers=None):
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        result, error = None, None
        try:
            response = requests.post(
                url=url,
                json=payload,
                headers=headers
            )
            if response.status_code == 200:
                result = response.json()
            else:
                error = response.text
        except Exception as e:
            error = f"Exception occurred while processing creating a float: {str(e)}"
            stack_trace = traceback.format_exc()
            logger.error(f"{error}\nStack Trace:\n{stack_trace}")

        return result, error