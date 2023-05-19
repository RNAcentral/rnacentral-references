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
import psycopg2
import sqlalchemy as sa

from database import DatabaseConnectionError, SQLError
from database.models import Job, JOB_STATUS_CHOICES


async def find_job_to_run(engine):
    """
    Find jobs that need to be performed and delivered to consumers for processing
    :param engine: params to connect to the db
    :return: sorted list of jobs
    """
    try:
        async with engine.acquire() as connection:
            try:
                query = (sa.select([Job.c.display_id, Job.c.status, Job.c.submitted])
                         .select_from(Job)
                         .where(Job.c.status == JOB_STATUS_CHOICES.pending)
                         .order_by(Job.c.submitted)
                         .limit(8))

                # get the eight oldest jobs
                output = []
                async for row in connection.execute(query):
                    output.append((row.display_id, row.submitted))

                return output

            except Exception as e:
                raise SQLError("Failed to find jobs in find_job_to_run()") from e

    except psycopg2.Error as e:
        raise DatabaseConnectionError(str(e)) from e


async def search_performed(engine, value):
    """
    Check if this value has already been searched
    :param engine: params to connect to the db
    :param value: the string to be searched
    :return: job_id
    """
    try:
        async with engine.acquire() as connection:
            try:
                sql_query = sa.text('''SELECT job_id FROM litscan_job WHERE job_id=:value''')
                async for row in connection.execute(sql_query, value=value.lower()):
                    return {"job_id": row.job_id}
            except Exception as e:
                raise SQLError("Failed to check if value exists for id = %s" % value) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in search_performed() for id = %s" % value) from e


async def save_job(engine, job_id, query):
    """
    Save metadata in the database
    :param engine: params to connect to the db
    :param job_id: the string that will be searched
    :param query: query used to filter results
    :return: job_id
    """
    try:
        async with engine.acquire() as connection:
            try:
                await connection.execute(
                    Job.insert().values(
                        job_id=job_id.lower(),
                        display_id=job_id,
                        submitted=datetime.datetime.now(),
                        status=JOB_STATUS_CHOICES.pending,
                        query=query
                    )
                )
                return job_id
            except Exception as e:
                raise SQLError("Failed to save job for id = %s to the database" % job_id) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in save_job() for id %s" % job_id) from e


async def set_job_status(engine, job_id, status):
    """
    Function to change job status.
    :param engine: params to connect to the db
    :param job_id: id of the job
    :param status: an option from consumer.JOB_CHUNK_STATUS
    :return: None
    """
    finished = None
    if status == JOB_STATUS_CHOICES.success or status == JOB_STATUS_CHOICES.error:
        finished = datetime.datetime.now()

    try:
        async with engine.acquire() as connection:
            try:
                if finished:
                    query = sa.text('''
                        UPDATE litscan_job
                        SET status=:status, finished=:finished
                        WHERE job_id=:job_id
                        RETURNING *;
                    ''')

                    job = None  # if connection didn't return any rows, return None
                    async for row in connection.execute(query, job_id=job_id, status=status, finished=finished):
                        job = row.job_id
                    return job
                else:
                    query = sa.text('''
                        UPDATE litscan_job
                        SET status=:status
                        WHERE job_id=:job_id
                        RETURNING *;
                    ''')

                    job = None  # if connection didn't return any rows, return None
                    async for row in connection.execute(query, job_id=job_id, status=status):
                        job = row.job_id
                    return job
            except Exception as e:
                raise SQLError("Failed to set_job_status, job_id = %s, status = %s" % (job_id, status)) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in set_job_status, job_id = %s" % job_id) from e


async def save_hit_count(engine, job_id, hit_count):
    """
    Function to save hit_count for a job.
    :param engine: params to connect to the db
    :param job_id: id of the job
    :param hit_count: number of hits
    :return: None
    """
    try:
        async with engine.acquire() as connection:
            try:
                query = sa.text('''UPDATE litscan_job SET hit_count=:hit_count WHERE job_id=:job_id''')
                await connection.execute(query, job_id=job_id, hit_count=hit_count)
            except Exception as e:
                raise SQLError("Failed to save_hit_count, job_id = %s and hit_count = %s" % (job_id, hit_count)) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in save_hit_count, job_id = %s" % job_id) from e


async def get_jobs(engine):
    """
    Function to get job info.
    :param engine: params to connect to the db
    :return: list of jobs
    """
    try:
        async with engine.acquire() as connection:
            results = []
            query = (sa.select([Job.c.job_id, Job.c.display_id]).select_from(Job).where(Job.c.hit_count > 0))
            try:
                async for row in connection.execute(query):
                    results.append({"job_id": row.job_id, "display_id": row.display_id})
                return results
            except Exception as e:
                raise SQLError("Failed to get jobs") from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in get_jobs()") from e


async def get_search_date(engine, job_id):
    """
    Function to get the date of the search
    :param engine: params to connect to the db
    :param job_id: id of the job
    :return: date of the search or none
    """
    try:
        async with engine.acquire() as connection:
            query = (sa.select([Job.c.finished]).select_from(Job).where(Job.c.job_id == job_id))
            finished = None
            try:
                async for row in connection.execute(query):
                    finished = row.finished
                return finished
            except Exception as e:
                raise SQLError("Failed to get the date of the search") from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in get_search_date()") from e


async def get_hit_count(engine, job_id):
    """
    Function to get hit_count
    :param engine: params to connect to the db
    :param job_id: id of the job
    :return: hit_count
    """
    try:
        async with engine.acquire() as connection:
            query = (sa.select([Job.c.hit_count]).select_from(Job).where(Job.c.job_id == job_id))
            try:
                async for row in connection.execute(query):
                    hit_count = row.hit_count
                return hit_count if hit_count else 0
            except Exception as e:
                raise SQLError("Failed to get hit_count") from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in get_hit_count()") from e


async def get_query(engine, job_id):
    """
    Function to get query
    :param engine: params to connect to the db
    :param job_id: id of the job
    :return: query
    """
    try:
        async with engine.acquire() as connection:
            sql_query = (sa.select([Job.c.query]).select_from(Job).where(Job.c.job_id == job_id))
            try:
                async for row in connection.execute(sql_query):
                    query = row.query
                return query
            except Exception as e:
                raise SQLError("Failed to get query") from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in get_query()") from e
