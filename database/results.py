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
import psycopg2
import sqlalchemy as sa

from database import DatabaseConnectionError, SQLError
from database.models import Result


async def save_results(engine, job_id, results):
    """
    Function to save results in DB
    :param engine: params to connect to the db
    :param job_id: id of the job
    :param results: list of dicts containing the results
    :return: None
    """
    try:
        async with engine.acquire() as connection:
            try:
                await connection.execute(Result.insert().values(results))
            except Exception as e:
                raise SQLError("Failed to save_results in the database, job_id = %s" % job_id) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in save_results, job_id = %s" % job_id) from e


async def get_job_results(engine, job_id):
    """
    Function to get job results
    :param engine: params to connect to the db
    :param job_id: id of the job
    :return: list of dicts containing the results
    """
    results = []
    sql = (sa.select([Result.c.title, Result.c.title_contains_value, Result.c.abstract, Result.c.body,
                      Result.c.author, Result.c.pmcid, Result.c.pmid, Result.c.doi, ])
           .select_from(Result)
           .where(Result.c.job_id == job_id))  # noqa

    try:
        async with engine.acquire() as connection:
            async for row in connection.execute(sql):
                # add result
                results.append({
                    'title': row[0],
                    'title_contains_value': row[1],
                    'abstract': row[2],
                    'body': row[3],
                    'author': row[4],
                    'pmcid': row[5],
                    'pmid': row[6],
                    'doi': row[7],
                })
            return results

    except psycopg2.Error as e:
        raise DatabaseConnectionError(str(e)) from e
