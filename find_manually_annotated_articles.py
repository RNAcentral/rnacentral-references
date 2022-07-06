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

from database.manually_annotated import save_manually_annotated
from database.job import search_performed
from database.results import get_pmid

load_dotenv()


async def find_manually_annotated_articles():
    """
    This function receives a list of articles that have been manually annotated and searches for
    these articles in the database. Results are saved in manually_annotated table.
    Run it with: python3 find_manually_annotated_articles.py <file>
    :return: None
    """
    # get parameter
    filename = None

    if len(sys.argv) == 1:
        print("Usage: python find_manually_annotated_articles.py <file>")
        exit()
    elif len(sys.argv) == 2:
        filename = sys.argv[1]
    else:
        print("Usage: python find_manually_annotated_articles.py <file>")
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

                # check if pmid and urs exist in database
                pmcid = await get_pmid(engine, pmid)
                job_id = await search_performed(engine, urs)

                if pmcid and job_id:
                    # save data in manually_annotated table
                    await save_manually_annotated(engine, {"pmcid": pmcid, "urs": job_id['job_id']})


if __name__ == '__main__':
    asyncio.run(find_manually_annotated_articles())
