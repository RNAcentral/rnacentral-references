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
from producer.views import submit_multiple_jobs
from database.metadata import search_metadata


class MultipleJobsTestCase(AioHTTPTestCase):
    """
    Recreate the test database by running:
    ENVIRONMENT=TEST python3 -m database

    Run these tests with:
    ENVIRONMENT=TEST python3 -m unittest producer.tests.test_multiple_jobs
    """
    async def get_application(self):
        logging.basicConfig(level=logging.ERROR)  # subdue messages like 'DEBUG:asyncio:Using selector: KqueueSelector'
        app = create_app()
        app.router.add_post('/api/multiple-jobs', submit_multiple_jobs.submit_multiple_jobs)
        return app

    @unittest_run_loop
    async def test_submit_multiple_jobs_post_success(self):
        data = json.dumps({"job_id": ["FOO.BAR"], "database": "test", "primary_id": "BAR.FOO"})
        async with self.client.post(path='/api/multiple-jobs', data=data) as response:
            assert response.status == 201
            text = await response.text()
            assert text == '{"job_id": ["foo.bar"], "name": "test", "primary_id": "bar.foo"}'

    @unittest_run_loop
    async def test_submit_multiple_jobs_missing_job_id(self):
        data = json.dumps({"database": "test", "primary_id": "BAR.FOO"})
        async with self.client.post(path='/api/multiple-jobs', data=data) as response:
            assert response.status == 400
            text = await response.text()
            assert text == '{"Error": "You must submit a list of job_ids as a parameter"}'

    @unittest_run_loop
    async def test_submit_multiple_jobs_wrong_job_id_type(self):
        data = json.dumps({"job_id": "foo.bar", "database": "test", "primary_id": "BAR.FOO"})
        async with self.client.post(path='/api/multiple-jobs', data=data) as response:
            assert response.status == 400
            text = await response.text()
            assert text == '{"Error": "You must submit a list of job_ids as a parameter"}'

    @unittest_run_loop
    async def test_submit_multiple_jobs_missing_database(self):
        data = json.dumps({"job_id": ["FOO.BAR"], "primary_id": "BAR.FOO"})
        async with self.client.post(path='/api/multiple-jobs', data=data) as response:
            assert response.status == 400
            text = await response.text()
            assert text == '{"Error": "You must submit the database name as a parameter"}'

    @unittest_run_loop
    async def test_submit_multiple_jobs_rescan_success(self):
        data = json.dumps({"job_id": ["FOO.BAR"], "database": "test", "primary_id": "BAR.FOO"})
        async with self.client.post(path='/api/multiple-jobs', data=data) as response:
            assert response.status == 201

        data = json.dumps({"job_id": ["FOO.BAR"], "database": "test", "primary_id": "BAR.FOO", "rescan": True})
        async with self.client.post(path='/api/multiple-jobs', data=data) as response:
            assert response.status == 201

    @unittest_run_loop
    async def test_submit_multiple_jobs_rescan_fail(self):
        data = json.dumps({"job_id": ["FOO.BAR"], "database": "test", "primary_id": "BAR.FOO", "rescan": "yes"})
        async with self.client.post(path='/api/multiple-jobs', data=data) as response:
            assert response.status == 400
            text = await response.text()
            assert text == '{"Error": "You must pass true or false in the rescan param"}'

    @unittest_run_loop
    async def test_submit_multiple_jobs_json_fail(self):
        data = "test"
        async with self.client.post(path='/api/multiple-jobs', data=data) as response:
            assert response.status == 400
            text = await response.text()
            assert text == '{"Error": "Please check the parameters used in the search"}'

    @unittest_run_loop
    async def test_submit_multiple_jobs_save_metadata(self):
        data = json.dumps({"job_id": ["FOO.BAR"], "database": "test", "primary_id": "BAR.FOO"})
        async with self.client.post(path='/api/multiple-jobs', data=data):
            find_metadata_1 = await search_metadata(self.app['engine'], "foo.bar", "test", "bar.foo")
            assert find_metadata_1 is not None

            find_metadata_2 = await search_metadata(self.app['engine'], "bar.foo", "test", None)
            assert find_metadata_2 is not None

