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

from database import DatabaseConnectionError, SQLError
from database.models import ManuallyAnnotated


async def save_manually_annotated(engine, results):
    """
    Function to save manually annotated articles
    :param engine: params to connect to the db
    :param results: dict containing manually annotated article
    :return: None
    """
    try:
        async with engine.acquire() as connection:
            try:
                await connection.execute(ManuallyAnnotated.insert().values(results))
            except Exception as e:
                raise SQLError(str(e)) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in save_manually_annotated") from e
