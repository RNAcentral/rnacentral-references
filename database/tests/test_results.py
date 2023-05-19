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
from database.models import Article, Job, JOB_STATUS_CHOICES, Result, AbstractSentence, BodySentence
from database.results import get_pmcid, get_pmcid_in_result, get_pmid, save_article, save_result, \
    save_abstract_sentences, save_body_sentences, get_articles, retracted_article, get_all_pmcid, get_all_pmid
from database.tests.test_base import DBTestCase


class ResultsTestCase(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_results
    """
    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            self.job_id = 'urs0002'
            self.display_id = 'URS0002'
            self.status = JOB_STATUS_CHOICES.pending
            await connection.execute(Job.insert().values(
                job_id=self.job_id, display_id=self.display_id, status=self.status)
            )
            self.pmcid = '123456780'
            self.pmid = '1234567'
            await connection.execute(Article.insert().values(pmcid=self.pmcid, pmid=self.pmid, retracted=False))
            await connection.execute(Result.insert().values(job_id=self.job_id, pmcid=self.pmcid))

    @unittest_run_loop
    async def test_article_saved(self):
        pmcid = await get_pmcid(self.app['engine'], self.pmcid)
        assert pmcid == self.pmcid

    @unittest_run_loop
    async def test_save_new_article(self):
        new_pmcid = "PMC123456"
        await save_article(self.app['engine'], {"pmcid": new_pmcid})
        async with self.app['engine'].acquire() as connection:
            query = sa.text('''SELECT pmcid FROM litscan_article''')
            result = []
            async for row in await connection.execute(query):
                result.append(row.pmcid)
        assert new_pmcid in result

    @unittest_run_loop
    async def test_result_saved(self):
        result = await get_pmcid_in_result(self.app['engine'], self.job_id)
        assert self.pmcid in result

    @unittest_run_loop
    async def test_save_new_result(self):
        new_pmcid = "PMC3456789"
        await save_article(self.app['engine'], {"pmcid": new_pmcid})
        new_result = await save_result(self.app['engine'], {"pmcid": new_pmcid, "job_id": self.job_id})
        assert new_result is not None

    @unittest_run_loop
    async def test_save_abstract_sentences(self):
        async with self.app['engine'].acquire() as connection:
            # get result_id
            query = (sa.select([Result.c.id]).select_from(Result).where(Result.c.job_id == self.job_id))
            async for row in connection.execute(query):
                result_id = row.id

            # save sentence
            sentences = [{"result_id": result_id, "sentence": "urs0002 found in an image or table"}]
            await save_abstract_sentences(self.app['engine'], sentences)

            # get sentence
            query = (sa.select([AbstractSentence.c.sentence])
                     .select_from(AbstractSentence)
                     .where(AbstractSentence.c.result_id == result_id))
            result = []
            async for row in await connection.execute(query):
                result.append(row.sentence)

            assert self.job_id in result[0]

    @unittest_run_loop
    async def test_save_body_sentences(self):
        async with self.app['engine'].acquire() as connection:
            # get result_id
            query = (sa.select([Result.c.id]).select_from(Result).where(Result.c.job_id == self.job_id))
            async for row in connection.execute(query):
                result_id = row.id

            # save sentence
            sentences = [{"result_id": result_id, "sentence": "urs0002 found in an image or table"}]
            await save_body_sentences(self.app['engine'], sentences)

            # get sentence
            query = (sa.select([BodySentence.c.sentence])
                     .select_from(BodySentence)
                     .where(BodySentence.c.result_id == result_id))
            result = []
            async for row in await connection.execute(query):
                result.append(row.sentence)

            assert self.job_id in result[0]

    @unittest_run_loop
    async def test_get_pmid(self):
        result = await get_pmid(self.app['engine'], self.pmid)
        assert self.pmcid == result

    @unittest_run_loop
    async def test_get_articles(self):
        result = await get_articles(self.app['engine'])
        assert ('pmcid', '123456780') in result[0].items()

    @unittest_run_loop
    async def test_get_all_pmcid(self):
        result = await get_all_pmcid(self.app['engine'])
        assert self.pmcid in result

    @unittest_run_loop
    async def test_retracted_article(self):
        await retracted_article(self.app['engine'], self.pmcid)

        async with self.app['engine'].acquire() as connection:
            # get retracted field
            query = (sa.select([Article.c.retracted]).select_from(Article).where(Article.c.pmcid == self.pmcid))
            async for row in connection.execute(query):
                result = row.retracted

            assert result is True

    @unittest_run_loop
    async def test_get_all_pmid(self):
        result = await get_all_pmid(self.app['engine'])
        assert {"pmcid": self.pmcid, "pmid": self.pmid} in result
