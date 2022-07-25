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


async def get_urs_count(engine):
    """
    Function to get the number of publications per urs_taxid
    :param engine: params to connect to the db
    :return: list of dicts containing urs -> number of articles
    """
    try:
        async with engine.acquire() as connection:
            try:
                result = []
                query = sa.text('''
                    SELECT UPPER(d.primary_id) as urs, SUM(j.hit_count) as total
                    FROM job j 
                    JOIN database d 
                    ON d.job_id=j.job_id 
                    WHERE j.hit_count>0 AND d.name='rnacentral' 
                    GROUP BY d.primary_id;
                ''')
                async for row in connection.execute(query):
                    result.append({"urs": row.urs, "hit_count": row.total})
                return result
            except Exception as e:
                raise SQLError(str(e)) from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in get_urs_count") from e
