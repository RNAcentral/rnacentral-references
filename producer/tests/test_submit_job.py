"""
Copyright [2009-2019] EMBL-European Bioinformatics Institute
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

import json
import logging

from aiohttp.test_utils import unittest_run_loop
from aiohttp.test_utils import AioHTTPTestCase

from producer.__main__ import create_app
from producer.views import submit_job


class SubmitJobTestCase(AioHTTPTestCase):
    """
    Recreate the test database by running:
    ENVIRONMENT=TEST python3 -m database

    Run these tests with:
    ENVIRONMENT=TEST python3 -m unittest producer.tests.test_submit_job
    """
    async def get_application(self):
        logging.basicConfig(level=logging.ERROR)  # subdue messages like 'DEBUG:asyncio:Using selector: KqueueSelector'
        app = create_app()
        app.router.add_post('/api/submit-job', submit_job.submit_job)
        return app

    @unittest_run_loop
    async def test_submit_job_post_success(self):
        data = json.dumps({"id": "FOO.BAR"})
        async with self.client.post(path='/api/submit-job', data=data) as response:
            assert response.status == 201
            text = await response.text()
            assert text == '{"job_id": "foo.bar"}'

    @unittest_run_loop
    async def test_submit_job_post_fail(self):
        data = json.dumps({"foo": "THIS_IS_NOT_A_VALID_KEY_VALUE"})
        async with self.client.post(path='/api/submit-job', data=data) as response:
            assert response.status == 400
            text = await response.text()
            assert text == '{"Error": "Id not found"}'

    @unittest_run_loop
    async def test_submit_rescan_fail(self):
        data = json.dumps({"id": "FOOBAR", "rescan": "yes"})
        async with self.client.post(path='/api/submit-job', data=data) as response:
            assert response.status == 400
            text = await response.text()
            assert text == '{"Error": "You must pass true or false in the rescan param"}'

    @unittest_run_loop
    async def test_submit_json_fail(self):
        data = "test"
        async with self.client.post(path='/api/submit-job', data=data) as response:
            assert response.status == 400
