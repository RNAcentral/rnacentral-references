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

import asyncio
import sys
import os

from aiopg.sa import create_engine
from dotenv import load_dotenv

from database.metadata import update_metadata
from database.results import get_manually_annotated_articles

load_dotenv()


async def find_manually_annotated_articles():
    """
    This function receives a list of articles that have been manually annotated and searches for
    these articles in the database. If an entry is found, the manually_annotated field is updated.
    Run it with: python3 find_manually_annotated_articles.py <file> <database>
    :return: None
    """
    # get parameters
    filename = None
    db_name = None

    if len(sys.argv) == 1 or len(sys.argv) == 2:
        print("You must pass the file and the database")
        exit()
    elif len(sys.argv) == 3:
        filename = sys.argv[1]
        db_name = sys.argv[2]
    else:
        print("Usage: python find_manually_annotated_articles.py <file> <database>")
        exit()

    # get credentials
    user = os.getenv("username")
    database = os.getenv("db")
    host = os.getenv("host")
    password = os.getenv("pass")

    async with create_engine(user=user, database=database, host=host, password=password) as engine:
        with open(filename, "r") as input_file:
            while line := input_file.readline():
                line = line.rstrip()
                line = line.split('|')
                urs = line[0].lower()
                pmid = line[1]

                results = await get_manually_annotated_articles(engine, urs, pmid, db_name)
                for item in results:
                    await update_metadata(engine, item['job_id'], item['primary_id'], db_name)


if __name__ == '__main__':
    asyncio.run(find_manually_annotated_articles())
