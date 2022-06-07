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

from database.metadata import metadata, search_metadata

load_dotenv()


async def save_metadata():
    """
    Save the metadata of a given database.
    Run it with: python3 save_metadata.py <file> <database>
    :return: None
    """
    # get parameters
    filename = None
    db_name = None

    if len(sys.argv) == 1 or len(sys.argv) == 2:
        print("You must pass the file that contains the ids and the database")
        exit()
    elif len(sys.argv) == 3:
        filename = sys.argv[1]
        db_name = sys.argv[2]
    else:
        print("Usage: python save_metadata.py <file> <database>")
        exit()

    # get credentials
    user = os.getenv("username")
    database = os.getenv("db")
    host = os.getenv("host")
    password = os.getenv("pass")

    async with create_engine(user=user, database=database, host=host, password=password) as engine:
        results = []
        temp_job_id = None
        temp_primary_id = None

        with open(filename, "r") as input_file:
            while line := input_file.readline():
                line = line.rstrip()
                line = line.split('|')
                job_id = line[0].lower()

                if len(line) == 3:
                    primary_id = line[1].lower()

                    # create metadata
                    if db_name == 'rfam':
                        if primary_id and primary_id != temp_primary_id:
                            results.append({"job_id": primary_id, "name": db_name, "primary_id": None})
                        if job_id and job_id != temp_job_id:
                            results.append({"job_id": job_id, "name": db_name, "primary_id": primary_id})
                        temp_job_id = job_id
                        temp_primary_id = primary_id if len(line) == 3 else None

                    elif db_name == 'refseq' or db_name == 'wormbase':
                        # TODO: Check if it is still necessary to query the database.
                        # The list of ids has been updated and duplicate ids have been removed.
                        if primary_id and not await search_metadata(engine, primary_id, db_name, None):
                            results.append({"job_id": primary_id, "name": db_name, "primary_id": None})
                        if job_id and not await search_metadata(engine, job_id, db_name, primary_id):
                            results.append({"job_id": job_id, "name": db_name, "primary_id": primary_id})

                    else:
                        results.append({"job_id": primary_id, "name": db_name, "primary_id": None})
                        results.append({"job_id": job_id, "name": db_name, "primary_id": primary_id})

                elif len(line) == 2:
                    urs = line[1].lower()

                    # create metadata
                    if db_name == 'rnacentral':
                        results.append({"job_id": job_id, "name": "rnacentral", "primary_id": urs})
                    else:
                        results.append({"job_id": job_id, "name": db_name, "primary_id": None})

                else:
                    # I'm using a single column file (with URS ids) to create part of the RNAcentral metadata
                    # create metadata
                    results.append({"job_id": job_id, "name": "rnacentral", "primary_id": None})

                if len(results) > 100:  # Values greater than 100 sometimes cause an error
                    try:
                        await metadata(engine, results)  # bulk insert into database
                        results = []
                    except Exception as e:
                        print(e)

        try:
            await metadata(engine, results)  # bulk insert into database
        except Exception as e:
            print(e)


if __name__ == '__main__':
    asyncio.run(save_metadata())
