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
from database.models import Database


async def metadata(engine, results):
    """
    Function to save metadata in DB
    :param engine: params to connect to the db
    :param results: list of dicts containing the metadata
    :return: None
    """
    try:
        async with engine.acquire() as connection:
            try:
                await connection.execute(Database.insert().values(results))
            except Exception as error:
                raise Exception(error)
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in metadata function") from e


async def search_metadata(engine, job_id, db_name, primary_id):
    """
    Check if this id already exists with this database and primary_id
    :param engine: params to connect to the db
    :param job_id: the string to be searched
    :param db_name: name of the Expert DB
    :param primary_id: primary Id of this job_id
    :return: id
    """
    try:
        async with engine.acquire() as connection:
            try:
                sql_query = (sa.select([Database.c.id])
                             .select_from(Database)
                             .where(Database.c.job_id == job_id, Database.c.name == db_name,
                                    Database.c.primary_id == primary_id))
                async for row in connection.execute(sql_query):
                    return {"id": row.id}
            except Exception as e:
                raise SQLError("Failed to check if value exists for job_id = %s "
                               "and db_name = %s" % (job_id, db_name)) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in search_metadata() for job_id = %s, "
                                      "db_name = %s and primary_id = %s" % (job_id, db_name, primary_id)) from e


async def update_metadata(engine, job_id, primary_id, database):
    """
    Function to update the metadata of a given search and specify that it is a manually annotated article
    :param engine: params to connect to the db
    :param job_id: id of the job
    :param primary_id: primary id of the job
    :param database: database name
    :return: None
    """
    try:
        async with engine.acquire() as connection:
            try:
                query = sa.text(
                    '''UPDATE database SET manually_annotated=TRUE 
                    WHERE job_id=:job_id AND primary_id=:primary_id AND name=:name'''
                )
                await connection.execute(query, job_id=job_id, primary_id=primary_id, name=database)
            except Exception as e:
                raise SQLError("Failed to update metadata, job_id = %s, primary_id = %s "
                               "and database = %s" % (job_id, primary_id, database)) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in update_metadata, job_id = %s, primary_id = %s "
                                      "and database = %s" % (job_id, primary_id, database)) from e
