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
from producer.views import job_result
from database.models import Article, Job, Result
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
            self.job_id = 'urs0005'
            self.pmcid = '123456780'
            await connection.execute(Job.insert().values(job_id=self.job_id))
            await connection.execute(Article.insert().values(pmcid=self.pmcid))
            await connection.execute(Result.insert().values(job_id=self.job_id, pmcid=self.pmcid))

    async def tearDownAsync(self):
        async with self.app['engine'].acquire() as connection:
            await connection.execute('DELETE FROM litscan_result')
            await connection.execute('DELETE FROM litscan_article')
            await connection.execute('DELETE FROM litscan_job')

        await super().tearDownAsync()

    @unittest_run_loop
    async def test_job_result_success(self):
        async with self.client.get(path='/api/results/urs0005') as response:
            assert response.status == 200
            text = await response.text()
            assert json.loads(text) == [{
                'job_id': self.job_id,
                'pmcid': self.pmcid,
                'title': None,
                'author': None,
                'pmid': None,
                'doi': None,
                'year': None,
                'journal': None,
                'score': None,
                'cited_by': None,
                'retracted': None,
                'id_in_title': None,
                'id_in_abstract': None,
                'id_in_body': None,
                'abstract_sentence': [],
                'body_sentence': []
            }]

    @unittest_run_loop
    async def test_job_result_empty(self):
        async with self.client.get(path='/api/results/foo') as response:
            text = await response.text()
            assert json.loads(text) == []
