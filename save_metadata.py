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

from database.job import search_performed
from database.metadata import metadata

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
        with open(filename, "r") as input_file:
            with open(db_name + "_missing_ids.txt", "w") as output_file:
                while line := input_file.readline():
                    line = line.rstrip()
                    line = line.split('|')
                    if len(line) == 3:
                        # check if these ids have already been searched
                        job_id = await search_performed(engine, line[0].lower())
                        primary_id = await search_performed(engine, line[1].lower())
                        urs = await search_performed(engine, line[2].lower())

                        if job_id and primary_id and urs:
                            job_id = job_id['job_id']
                            primary_id = primary_id['job_id']
                            urs = urs['job_id']

                            # create metadata
                            results.append({"job_id": urs, "name": "rnacentral", "primary_id": None})
                            results.append({"job_id": primary_id, "name": db_name, "primary_id": None})
                            results.append({"job_id": primary_id, "name": "rnacentral", "primary_id": urs})
                            results.append({"job_id": job_id, "name": "rnacentral", "primary_id": urs})
                            results.append({"job_id": job_id, "name": db_name, "primary_id": primary_id})
                        else:
                            # add missing ids to output_file
                            if not job_id:
                                output_file.write(line[0] + '\n')
                            if not primary_id:
                                output_file.write(line[1] + '\n')
                            if not urs:
                                output_file.write(line[2] + '\n')

                    else:
                        # check if these ids have already been searched
                        job_id = await search_performed(engine, line[0].lower())
                        urs = await search_performed(engine, line[1].lower())

                        if job_id and urs:
                            job_id = job_id['job_id']
                            urs = urs['job_id']

                            # create metadata
                            results.append({"job_id": urs, "name": "rnacentral", "primary_id": None})
                            results.append({"job_id": job_id, "name": "rnacentral", "primary_id": urs})
                            results.append({"job_id": job_id, "name": db_name, "primary_id": None})
                        else:
                            # add missing ids to output_file
                            if not job_id:
                                output_file.write(line[0] + '\n')
                            if not urs:
                                output_file.write(line[1] + '\n')

        # bulk insert into database
        await metadata(engine, results)


if __name__ == '__main__':
    asyncio.run(save_metadata())
