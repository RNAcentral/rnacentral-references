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
import psycopg2
import sqlalchemy as sa

from database import DatabaseConnectionError, SQLError
from database.models import Job, JOB_STATUS_CHOICES


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


async def save_job(engine, value):
    """
    Save metadata in the database
    :param engine: params to connect to the db
    :param value: the string that will be saved
    :return: string saved in DB
    """
    try:
        async with engine.acquire() as connection:
            try:
                await connection.execute(
                    Job.insert().values(
                        job_id=value,
                        submitted=datetime.datetime.now(),
                        status=JOB_STATUS_CHOICES.started
                    )
                )
                return value
            except Exception as e:
                raise SQLError("Failed to save job for id = %s to the database" % value) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in save_job() for id %s" % value) from e
