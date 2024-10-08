"""
Copyright [2009-present] EMBL-European Bioinformatics Institute
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
     http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import asyncio
import json
import logging

from aiohttp import ClientConnectionError, ClientResponseError
from aiohttp import test_utils, web
from .settings import ENVIRONMENT


class ConsumerConnectionError(Exception):
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


async def delegate_job_to_consumer(consumer_ip, consumer_port, job_id, session):
    """
    Function for submitting a job to a consumer

    :param consumer_ip: consumer IP address
    :param consumer_port: consumer port
    :param job_id: id of the job
    :param session: aiohttp session
    :return: nothing is returned here unless something goes wrong :|
    """
    # prepare the data for the request
    url = f"http://{consumer_ip}:{consumer_port}/submit-job"
    json_data = json.dumps({"job_id": job_id})
    headers = {"content-type": "application/json"}

    try:
        if ENVIRONMENT != "TEST":
            logging.debug(f"Queuing job to consumer: url = {url}, json_data = {json_data}")
            response = await session.post(url, data=json_data, headers=headers, timeout=10)

            # if the response status is >= 400, log it and raise an error
            if response.status >= 400:
                text = await response.text()
                raise ConsumerConnectionError(f"Error from consumer: {text}")

            return

        else:
            # in the TEST environment, mock the request
            logging.debug(f"Queuing job to consumer in TEST environment: url = {url}, json_data = {json_data}")
            test_utils.make_mocked_request("POST", url, headers=headers)
            await asyncio.sleep(1)
            return web.Response(status=200)

    except ClientConnectionError:
        logging.error(f"Connection error while submitting job {job_id} to {consumer_ip}:{consumer_port}.")
    except ClientResponseError as e:
        logging.error(f"Invalid response from consumer {consumer_ip}:{consumer_port} with status {e.status}.")
    except asyncio.TimeoutError:
        logging.error(f"Timeout while submitting job {job_id} to {consumer_ip}:{consumer_port}.")
    except Exception as e:
        logging.error(f"Unexpected error in delegate_job_to_consumer: {str(e)}")
