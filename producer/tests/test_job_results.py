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

import datetime
import json
import logging

from aiohttp.test_utils import unittest_run_loop
from aiohttp.test_utils import AioHTTPTestCase

from producer.__main__ import create_app
from producer.views import job_result
from database.models import Job, JOB_STATUS_CHOICES, Result
from database.settings import get_postgres_credentials


class JobResultsTestCase(AioHTTPTestCase):
    """
    Recreate the test database by running:
    ENVIRONMENT=TEST python3 -m database

    Run these tests with:
    ENVIRONMENT=TEST python3 -m unittest producer.tests.test_job_results
    """
    async def get_application(self):
        logging.basicConfig(level=logging.ERROR)  # subdue messages like 'DEBUG:asyncio:Using selector: KqueueSelector'
        app = create_app()
        settings = get_postgres_credentials(ENVIRONMENT='TEST')
        app.update(name='test', settings=settings)
        app.router.add_get('/api/results/{job_id:[A-Za-z0-9_-]+}', job_result.job_result)
        return app

    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            await connection.execute(
                Job.insert().values(
                    job_id="mir-21",
                    submitted=datetime.datetime.now(),
                    status=JOB_STATUS_CHOICES.started
                )
            )

            await connection.scalar(
                Result.insert().values(
                    job_id="mir-21",
                    title='Lorem ipsum dolor sit amet',
                    title_value=False,
                    abstract='',
                    abstract_value=False,
                    body='Lorem ipsum miR-21 dolor',
                    body_value=True,
                    author='de Tal, Fulano',
                    pmcid='123456789',
                    pmid='123456789',
                    doi='10.1234/journal.123',
                    year=2021,
                    journal='foo',
                    count=2
                )
            )

    async def tearDownAsync(self):
        async with self.app['engine'].acquire() as connection:
            await connection.execute('DELETE FROM result')
            await connection.execute('DELETE FROM job')

        await super().tearDownAsync()

    @unittest_run_loop
    async def test_job_result_success(self):
        async with self.client.get(path='/api/results/mir-21') as response:
            assert response.status == 200
            text = await response.text()
            assert json.loads(text) == [{
                "title": "Lorem ipsum dolor sit amet",
                "title_value": False,
                "abstract": "",
                "abstract_value": False,
                "body": "Lorem ipsum miR-21 dolor",
                "body_value": True,
                "author": "de Tal, Fulano",
                "pmcid": "123456789",
                "pmid": "123456789",
                "doi": "10.1234/journal.123",
                "year": 2021,
                "journal": "foo",
                "count": 2
            }]

    @unittest_run_loop
    async def test_job_result_empty(self):
        async with self.client.get(path='/api/results/foo') as response:
            text = await response.text()
            assert json.loads(text) == []
