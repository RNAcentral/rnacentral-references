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
import sqlalchemy as sa

from aiohttp.test_utils import unittest_run_loop
from database.organism import load_organism, find_pmid_organism, save_organism
from database.models import Article, LoadOrganism, Organism
from database.tests.test_base import DBTestCase


class OrganismTestCase(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_organism
    """
    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            self.organism = 9606
            self.pmid = "9999000"

            self.articles = [
                {"pmcid": "123456700", "pmid": "1234567"},
                {"pmcid": "123456701", "pmid": "1111222"},
            ]
            await connection.execute(Article.insert().values(self.articles))

            self.organisms = [
                {"pmid": "1234567", "organism": 9606},
                {"pmid": "1234567", "organism": 559292},
                {"pmid": "7654321", "organism": 9606},
            ]
            await connection.execute(LoadOrganism.insert().values(self.organisms))

    @unittest_run_loop
    async def test_load_organism(self):
        await load_organism(self.app['engine'], {"organism": self.organism, "pmid": self.pmid})

        async with self.app['engine'].acquire() as connection:
            # get load_organism
            query = (sa.select([sa.func.count(LoadOrganism.c.id)]).select_from(LoadOrganism))
            async for row in connection.execute(query):
                result = row._row[0]
            assert result == 4  # 3 from setUpAsync + 1 here

    @unittest_run_loop
    async def test_find_pmid_organism(self):
        organisms = await find_pmid_organism(self.app['engine'], "1234567")
        assert organisms == [9606, 559292]

    @unittest_run_loop
    async def test_find_pmid_organism_empty(self):
        organisms = await find_pmid_organism(self.app['engine'], self.pmid)
        assert organisms == []

    @unittest_run_loop
    async def test_save_organism(self):
        await save_organism(self.app['engine'], {"pmcid": "123456701", "organism": 9606})

        async with self.app['engine'].acquire() as connection:
            # get organism
            query = (sa.select([Organism.c.pmcid, Organism.c.organism]).select_from(Organism))
            results = []
            async for row in connection.execute(query):
                results.append({"pmcid": row.pmcid, "organism": row.organism})
            assert results == [{"pmcid": "123456701", "organism": 9606}]
