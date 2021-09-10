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

import aiohttp
import asyncio
import json
import logging

from aiohttp import test_utils, web
from .settings import ENVIRONMENT


class ConsumerConnectionError(Exception):
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


async def delegate_job_to_consumer(consumer_ip, consumer_port, job_id):
    """
    Function for submitting a job to a consumer
    :param consumer_ip: consumer IP address
    :param consumer_port: consumer port
    :param job_id: id of the job
    :return: nothing is returned here unless something goes wrong :|
    """
    # prepare the data for request
    url = "http://" + str(consumer_ip) + ':' + str(consumer_port) + '/submit-job'
    json_data = json.dumps({"job_id": job_id})
    headers = {'content-type': 'application/json'}

    if ENVIRONMENT != 'TEST':
        async with aiohttp.ClientSession() as session:
            logging.debug("Queuing job to consumer: url = {}, json_data = {}".format(url, json_data))
            response = await session.post(url, data=json_data, headers=headers)
    else:
        # in TEST environment mock the request
        logging.debug("Queuing job to consumer: url = {}, json_data = {}".format(url, json_data))
        test_utils.make_mocked_request('POST', url, headers=headers)
        await asyncio.sleep(1)
        response = web.Response(status=200)

    if response.status >= 400:
        text = await response.text()
        raise ConsumerConnectionError(text)
