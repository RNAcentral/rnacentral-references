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
from database.job import save_job
from database.metadata import metadata, search_metadata
from database.tests.test_base import DBTestCase


class SaveMetadataTestCase(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_jobs.SaveMetadataTestCase
    """
    async def setUpAsync(self):
        await super().setUpAsync()

    @unittest_run_loop
    async def test_save_job(self):
        job_id = await save_job(
            self.app['engine'],
            job_id="foo.bar"
        )
        urs = await save_job(
            self.app['engine'],
            job_id="urs001"
        )
        results = [
            {"job_id": job_id, "name": "rnacentral", "primary_id": urs},
            {"job_id": urs, "name": "rnacentral", "primary_id": None},
            {"job_id": job_id, "name": "test", "primary_id": None},
        ]
        await metadata(self.app['engine'], results=results)

        find_metadata_1 = await search_metadata(self.app['engine'], job_id, "test", None)
        assert find_metadata_1 is not None

        find_metadata_2 = await search_metadata(self.app['engine'], job_id, "rnacentral", urs)
        assert find_metadata_2 is not None

        find_metadata_3 = await search_metadata(self.app['engine'], urs, "rnacentral", None)
        assert find_metadata_3 is not None
