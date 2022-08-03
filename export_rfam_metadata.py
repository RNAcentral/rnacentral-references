import asyncio
import csv
import os

from aiopg.sa import create_engine
from database.metadata import metadata, search_metadata
from dotenv import load_dotenv

load_dotenv()


async def export_rfam_metadata():
    """
    Extract the ids from a csv file to save in the RNAcentral-references database.
    :return: None
    """
    # get credentials
    user = os.getenv("username")
    database = os.getenv("db")
    host = os.getenv("host")
    password = os.getenv("pass")

    async with create_engine(user=user, database=database, host=host, password=password) as engine:
        results = []
        database = "rfam"

        with open("Rfam Families and Aliases - Sheet1.csv", "r") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            next(csv_reader)

            for line in csv_reader:
                external_id = line[0].lower()
                if external_id and not await search_metadata(engine, external_id, database, None):
                    results.append({"job_id": external_id, "name": database, "primary_id": None})

                for item in line[1:]:
                    job_id = item.lower() if item else None
                    if external_id and job_id and not await search_metadata(engine, job_id, database, external_id):
                        results.append({"job_id": job_id, "name": database, "primary_id": external_id})

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


if __name__ == "__main__":
    asyncio.run(export_rfam_metadata())
