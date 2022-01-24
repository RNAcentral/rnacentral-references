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
from database.models import Database, Job, JOB_STATUS_CHOICES


async def find_job_to_run(engine):
    """
    Find jobs that need to be performed and delivered to consumers for processing
    :param engine: params to connect to the db
    :return: sorted list of jobs
    """
    try:
        async with engine.acquire() as connection:
            try:
                query = (sa.select([Job.c.job_id, Job.c.status, Job.c.submitted])
                         .select_from(Job)
                         .where(Job.c.status == JOB_STATUS_CHOICES.pending)
                         .order_by(Job.c.submitted)
                         .limit(8))

                # get the eight oldest jobs
                output = []
                async for row in connection.execute(query):
                    output.append((row.job_id, row.submitted))

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
                sql_query = sa.select([Job.c.job_id]).select_from(Job).where(Job.c.job_id == value)
                async for row in connection.execute(sql_query):
                    return {"job_id": row.job_id}
            except Exception as e:
                raise SQLError("Failed to check if value exists for id = %s" % value) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in search_performed() for id = %s" % value) from e


async def save_job(engine, job_id, primary_id):
    """
    Save metadata in the database
    :param engine: params to connect to the db
    :param job_id: the string that will be searched
    :param primary_id: job_id can be related to another job_id
    :return: job_id
    """
    try:
        print(primary_id)
        async with engine.acquire() as connection:
            try:
                await connection.execute(
                    Job.insert().values(
                        job_id=job_id,
                        submitted=datetime.datetime.now(),
                        status=JOB_STATUS_CHOICES.pending,
                        primary_id=primary_id
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
                        UPDATE job
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
                        UPDATE job
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
                query = sa.text('''UPDATE job SET hit_count=:hit_count WHERE job_id=:job_id''')
                await connection.execute(query, job_id=job_id, hit_count=hit_count)
            except Exception as e:
                raise SQLError("Failed to save_hit_count, job_id = %s and hit_count = %s" % (job_id, hit_count)) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in save_hit_count, job_id = %s" % job_id) from e


async def get_jobs(engine):
    """
    Function to get job ids.
    :param engine: params to connect to the db
    :return: list of jobs
    """
    try:
        async with engine.acquire() as connection:
            results = []
            try:
                async for row in connection.execute(sa.select([Job.c.job_id]).select_from(Job)):
                    results.append(row.job_id)
                return results
            except Exception as e:
                raise SQLError("Failed to get jobs") from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in get_jobs()") from e


async def search_db_name_with_job_id(engine, job_id, db_name):
    """
    Check if this id already exists with this db_name in the database
    :param engine: params to connect to the db
    :param job_id: the string to be searched
    :param db_name: Name of the Expert DB
    :return: id
    """
    try:
        async with engine.acquire() as connection:
            try:
                sql_query = (sa.select([Database.c.id])
                             .select_from(Database)
                             .where(Database.c.job_id == job_id, Database.c.name == db_name))
                async for row in connection.execute(sql_query):
                    return {"id": row.id}
            except Exception as e:
                raise SQLError("Failed to check if value exists for job_id = %s "
                               "and db_name = %s" % (job_id, db_name)) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in search_db_name_with_job_id() for "
                                      "job_id = %s and db_name = %s" % (job_id, db_name)) from e


async def save_db_with_job_id(engine, job_id, db_name):
    """
    Save job_id and database name
    :param engine: params to connect to the db
    :param job_id: the string that will be searched
    :param db_name: database associated with this job_id
    :return: true in case of success
    """
    try:
        async with engine.acquire() as connection:
            try:
                await connection.execute(Database.insert().values(job_id=job_id, name=db_name))
                return True
            except Exception as e:
                raise SQLError("Failed to save DB name for job_id = %s and db_name = %s" % (job_id, db_name)) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in save_db_with_job_id() for "
                                      "job_id = %s and db_name = %s" % (job_id, db_name)) from e


async def get_database(engine, job_id):
    """
    Function to get a list of dbs associated with an id
    :param engine: params to connect to the db
    :param job_id: id of the job
    :return: list of dbs
    """
    try:
        async with engine.acquire() as connection:
            results = []
            sql_query = sa.select([Database.c.name]).select_from(Database).where(Database.c.job_id == job_id)
            try:
                async for row in connection.execute(sql_query):
                    results.append(row.name)
                return results
            except Exception as e:
                raise SQLError("Failed to get dbs for job_id = %s" % job_id) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in get_database() for job_id = %s" % job_id) from e


async def get_primary_id(engine, job_id):
    """
    Function to check if the job_id has a primary_id
    :param engine: params to connect to the db
    :param job_id: id of the job
    :return: primary_id, if any
    """
    try:
        async with engine.acquire() as connection:
            try:
                sql_query = sa.select([Job.c.primary_id]).select_from(Job).where(Job.c.job_id == job_id)
                async for row in connection.execute(sql_query):
                    return row.primary_id
            except Exception as e:
                raise SQLError("Failed to get primary_id for id = %s" % job_id) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in get_primary_id for job_id = %s" % job_id) from e
