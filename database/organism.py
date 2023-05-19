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
import logging
import psycopg2
import sqlalchemy as sa

from database import DatabaseConnectionError
from database.models import LoadOrganism, Organism


async def load_organism(engine, result):
    """
    Function to load organism in the database
    :param engine: params to connect to the db
    :param result: dict containing the result
    :return: None
    """
    try:
        async with engine.acquire() as connection:
            try:
                await connection.execute(LoadOrganism.insert().values(result))
            except Exception as e:
                logging.debug("Failed to load_organism in the database. Error: {}.".format(e))
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in load_organism") from e


async def find_pmid_organism(engine, pmid):
    """
    Function to find organisms for a specif article
    :param engine: params to connect to the db
    :param pmid: id of the PM
    :return: list of organisms
    """
    query = (sa.select([LoadOrganism.c.organism]).select_from(LoadOrganism).where(LoadOrganism.c.pmid == pmid))  # noqa
    organisms = []
    try:
        async with engine.acquire() as connection:
            async for row in connection.execute(query):
                organisms.append(row.organism)
            return organisms
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in find_pmid_organism()") from e


async def save_organism(engine, results):
    """
    Function to save organisms identified in an article
    :param engine: params to connect to the db
    :param results: dict containing results
    :return: None
    """
    try:
        async with engine.acquire() as connection:
            try:
                await connection.execute(Organism.insert().values(results))
            except Exception as e:
                logging.debug("Failed to save_organism in the database. Error: {}.".format(e))
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in save_organism") from e
