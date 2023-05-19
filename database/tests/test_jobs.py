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

from aiohttp.test_utils import unittest_run_loop
from database.models import Job, JOB_STATUS_CHOICES
from database.job import find_job_to_run, get_hit_count, get_jobs, get_search_date, save_job, save_hit_count, \
    search_performed, set_job_status
from database.tests.test_base import DBTestCase


class JobTestCase(DBTestCase):
    """
    Run this test with the following command:
    ENVIRONMENT=TEST python -m unittest database.tests.test_jobs
    """
    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            self.job_id = 'urs0001'
            self.display_id = 'URS0001'
            self.status = JOB_STATUS_CHOICES.pending
            await connection.execute(Job.insert().values(
                job_id=self.job_id, display_id=self.display_id, status=self.status)
            )

    @unittest_run_loop
    async def test_save_new_job(self):
        job_id = await save_job(self.app['engine'], job_id="foo", query="")
        assert job_id == "foo"

    @unittest_run_loop
    async def test_search_performed(self):
        job = await search_performed(self.app['engine'], self.job_id)
        assert job["job_id"] == self.job_id

    @unittest_run_loop
    async def test_find_job_to_run(self):
        find_job = await find_job_to_run(self.app['engine'])
        assert find_job[0][0] == self.display_id

    @unittest_run_loop
    async def test_set_job_status_success(self):
        job = await set_job_status(self.app['engine'], self.job_id, JOB_STATUS_CHOICES.success)
        assert job == self.job_id

    @unittest_run_loop
    async def test_get_jobs(self):
        # should return jobs with hit_count > 0
        await save_job(self.app['engine'], job_id="FOOBar", query="")  # this id should not appear in the results
        await save_hit_count(self.app['engine'], self.job_id, 5)
        jobs = await get_jobs(self.app['engine'])
        assert jobs == [{'job_id': self.job_id, 'display_id': self.display_id}]

    @unittest_run_loop
    async def test_check_date(self):
        await set_job_status(self.app['engine'], self.job_id, JOB_STATUS_CHOICES.success)
        today = datetime.date.today().strftime("%Y-%m-%d")
        search_date = await get_search_date(self.app['engine'], self.job_id)
        assert search_date.strftime("%Y-%m-%d") == today

    @unittest_run_loop
    async def test_no_date(self):
        search_date = await get_search_date(self.app['engine'], self.job_id)
        assert search_date is None

    @unittest_run_loop
    async def test_save_and_get_hit_count(self):
        await save_hit_count(self.app['engine'], self.job_id, 10)
        hit_count = await get_hit_count(self.app['engine'], self.job_id)
        assert hit_count == 10

    @unittest_run_loop
    async def test_no_hit_count(self):
        hit_count = await get_hit_count(self.app['engine'], self.job_id)
        assert hit_count == 0
