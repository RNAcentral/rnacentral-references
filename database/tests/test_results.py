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
import datetime
import sqlalchemy as sa

from aiohttp.test_utils import unittest_run_loop
from database.models import Job, JOB_STATUS_CHOICES
from database.results import save_results
from database.tests.test_base import DBTestCase


class SaveResults(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_jobs.SaveResults
    """
    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            self.job_id = 'ipsum'

            await connection.execute(
                Job.insert().values(
                    job_id=self.job_id,
                    submitted=datetime.datetime.now(),
                    status=JOB_STATUS_CHOICES.success
                )
            )

    @unittest_run_loop
    async def test_save_result(self):
        results = [{
            'title': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit',
            'abstract': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit',
            'body': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit',
            'pmid': '123456789',
            'doi': '12.3456/7890-9999-9-9',
            'job_id': self.job_id
        }]
        await save_results(self.app['engine'], self.job_id, results)

        async with self.app['engine'].acquire() as connection:
            query = sa.text('''
                SELECT pmid
                FROM result
                WHERE job_id=:job_id
            ''')

            async for row in await connection.execute(query, job_id=self.job_id):
                assert row.pmid == '123456789'
