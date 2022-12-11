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

from aiohttp.test_utils import unittest_run_loop
from database.metadata import metadata, search_metadata
from database.models import Job
from database.tests.test_base import DBTestCase


class MetadataTestCase(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_metadata
    """
    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            await connection.execute(Job.insert().values(job_id='foo.bar'))
            await connection.execute(Job.insert().values(job_id='urs003'))

            results = [
                {"job_id": "foo.bar", "name": "rnacentral", "primary_id": "urs003"},
                {"job_id": "urs003", "name": "rnacentral", "primary_id": None},
                {"job_id": "foo.bar", "name": "test", "primary_id": None},
            ]
            await metadata(self.app['engine'], results=results)

    @unittest_run_loop
    async def test_find_job_id_with_expert_db(self):
        find_metadata_1 = await search_metadata(self.app['engine'], "foo.bar", "test", None)
        assert find_metadata_1 is not None

    @unittest_run_loop
    async def test_find_job_id_with_rnacentral(self):
        find_metadata_2 = await search_metadata(self.app['engine'], "foo.bar", "rnacentral", 'urs003')
        assert find_metadata_2 is not None

    @unittest_run_loop
    async def test_find_urs(self):
        find_metadata_3 = await search_metadata(self.app['engine'], "urs003", "rnacentral", None)
        assert find_metadata_3 is not None

    @unittest_run_loop
    async def test_wrong_job_id(self):
        wrong_job = await search_metadata(self.app['engine'], "wrong_job", "rnacentral", None)
        assert wrong_job is None
