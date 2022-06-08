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


async def get_pmcid(engine, job_id):
    """
    Function to get a list of pmcid from a given job_id
    :param engine: params to connect to the db
    :param job_id: id of the job
    :return: list of pmcid
    """
    results = []
    query = (sa.select([Result.c.pmcid]).select_from(Result).where(Result.c.job_id == job_id))  # noqa
    try:
        async with engine.acquire() as connection:
            async for row in connection.execute(query):
                results.append(row.pmcid)
            return results
    except psycopg2.Error as e:
        raise DatabaseConnectionError(str(e)) from e


async def get_job_results(engine, job_id):
    """
    Function to get job results
    :param engine: params to connect to the db
    :param job_id: id of the job
    :return: list of dicts containing the results
    """
    results = []
    sql = (sa.select([Result.c.title, Result.c.title_value, Result.c.abstract, Result.c.abstract_value, Result.c.body,
                      Result.c.body_value, Result.c.author, Result.c.pmcid, Result.c.pmid, Result.c.doi, Result.c.year,
                      Result.c.journal,Result.c.score, Result.c.cited_by])
           .select_from(Result)
           .where(Result.c.job_id == job_id))  # noqa

    try:
        async with engine.acquire() as connection:
            async for row in connection.execute(sql):
                # add result
                results.append({
                    'title': row[0],
                    'title_value': row[1],
                    'abstract': row[2],
                    'abstract_value': row[3],
                    'body': row[4],
                    'body_value': row[5],
                    'author': row[6],
                    'pmcid': row[7],
                    'pmid': row[8],
                    'doi': row[9],
                    'year': row[10],
                    'journal': row[11],
                    'score': row[12],
                    'cited_by': row[13],
                })
            return results

    except psycopg2.Error as e:
        raise DatabaseConnectionError(str(e)) from e
