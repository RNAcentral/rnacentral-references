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
import sqlalchemy as sa

from aiohttp.test_utils import unittest_run_loop
from database.manually_annotated import save_manually_annotated
from database.models import Article, Job, ManuallyAnnotated
from database.tests.test_base import DBTestCase


class ManuallyAnnotatedTestCase(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_manually_annotated
    """
    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            self.job_id = 'urs0004'
            self.display_id = 'URS0004'
            await connection.execute(Job.insert().values(job_id=self.job_id, display_id=self.display_id))
            self.pmcid = '123456700'
            await connection.execute(Article.insert().values(pmcid=self.pmcid))

    @unittest_run_loop
    async def test_save_manually_annotated(self):
        await save_manually_annotated(self.app['engine'], {"pmcid": self.pmcid, "urs": self.job_id})

        async with self.app['engine'].acquire() as connection:
            # get manually_annotated
            query = (sa.select([ManuallyAnnotated.c.urs]).select_from(ManuallyAnnotated))
            async for row in connection.execute(query):
                urs = row.urs
            assert urs == self.job_id
