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
import sqlalchemy as sa

from aiohttp.test_utils import unittest_run_loop
from database.models import Job, JOB_STATUS_CHOICES
from database.job import find_job_to_run, get_hit_count, get_jobs, get_search_date, save_job, save_hit_count, \
    search_performed, set_job_status
from database.tests.test_base import DBTestCase


class SaveJobTestCase(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_jobs.SaveJobTestCase
    """
    async def setUpAsync(self):
        await super().setUpAsync()

    @unittest_run_loop
    async def test_save_job(self):
        job_id = await save_job(
            self.app['engine'],
            job_id="foo"
        )
        assert job_id == "foo"


class SearchPerformedTestCase(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_jobs.SearchPerformedTestCase
    """
    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            await connection.execute(
                Job.insert().values(
                    job_id='bar',
                    submitted=datetime.datetime.now(),
                    status=JOB_STATUS_CHOICES.success
                )
            )

    @unittest_run_loop
    async def test_search_performed(self):
        job = await search_performed(self.app['engine'], 'bar')
        assert job is not None


class FindJobTestCase(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_jobs.FindJobTestCase
    """
    async def setUpAsync(self):
        await super().setUpAsync()

    @unittest_run_loop
    async def test_save_job(self):
        job_id = await save_job(
            self.app['engine'],
            job_id="foo"
        )
        find_job = await find_job_to_run(self.app['engine'])
        assert find_job[0][0] == job_id


class SetJobStatusTestCase(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_job_chunks.SetJobStatusTestCase
    """
    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            await connection.execute(
                Job.insert().values(
                    job_id='foo',
                    submitted=datetime.datetime.now(),
                    status=JOB_STATUS_CHOICES.pending
                )
            )

    @unittest_run_loop
    async def test_set_job_status_started(self):
        job = await set_job_status(self.app['engine'], 'foo', JOB_STATUS_CHOICES.started)
        assert job == 'foo'


class SaveHitCountTestCase(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_job_chunks.SaveHitCountTestCase
    """
    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            await connection.execute(
                Job.insert().values(
                    job_id='testHitCount',
                    submitted=datetime.datetime.now(),
                    status=JOB_STATUS_CHOICES.pending
                )
            )

    @unittest_run_loop
    async def test_save_hit_count(self):
        await save_hit_count(self.app['engine'], 'testHitCount', 10)

        async with self.app['engine'].acquire() as connection:
            query = sa.text('''SELECT hit_count FROM job WHERE job_id=:job_id''')

            async for row in await connection.execute(query, job_id='testHitCount'):
                assert row.hit_count is 10
                break


class GetJobsTestCase(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_jobs.GetJobsTestCase
    """
    async def setUpAsync(self):
        await super().setUpAsync()

    @unittest_run_loop
    async def test_save_job(self):
        await save_job(
            self.app['engine'],
            job_id="FOO"
        )

        await save_job(
            self.app['engine'],
            job_id="Bar"
        )

        jobs = await get_jobs(self.app['engine'])
        assert jobs == [{'job_id': 'foo', 'display_id': 'FOO'}, {'job_id': 'bar', 'display_id': 'Bar'}]


class GetSearchDateTestCase(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_jobs.GetSearchDateTestCase
    """
    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            await connection.execute(
                Job.insert().values(
                    job_id='testsearchdate',
                    submitted=datetime.datetime.now() - datetime.timedelta(minutes=10),
                    finished=datetime.datetime.now(),
                    status=JOB_STATUS_CHOICES.success
                )
            )

    @unittest_run_loop
    async def test_check_date(self):
        today = datetime.date.today().strftime("%Y-%m-%d")
        search_date = await get_search_date(self.app['engine'], 'testsearchdate')
        assert search_date.strftime("%Y-%m-%d") == today

    @unittest_run_loop
    async def test_no_date(self):
        search_date = await get_search_date(self.app['engine'], 'nosearchdate')
        assert search_date is None


class GetHitCountTestCase(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_jobs.GetHitCountTestCase
    """
    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            await connection.execute(
                Job.insert().values(
                    job_id='testhitcount',
                    submitted=datetime.datetime.now() - datetime.timedelta(minutes=10),
                    finished=datetime.datetime.now(),
                    status=JOB_STATUS_CHOICES.success,
                    hit_count=3
                )
            )

    @unittest_run_loop
    async def test_hit_count(self):
        hit_count = await get_hit_count(self.app['engine'], 'testhitcount')
        assert hit_count == 3

    @unittest_run_loop
    async def test_no_hit_count(self):
        hit_count = await get_hit_count(self.app['engine'], 'nohitcount')
        assert hit_count == 0
