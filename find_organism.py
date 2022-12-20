import asyncio
import csv
import os

from aiopg.sa import create_engine
from dotenv import load_dotenv
from database.organism import find_pmid_organism, save_organism
from database.results import get_all_pmid

load_dotenv()


async def main():
    """
    Find organisms. Data extracted from https://organisms.jensenlab.org
    :return: None
    """

    # get credentials
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DATABASE")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")

    async with create_engine(user=user, password=password, database=database, host=host, port=port) as engine:
        pmid_list = await get_all_pmid(engine)

        for item in pmid_list:
            organisms = await find_pmid_organism(engine, item["pmid"])
            results = []

            for organism in organisms:
                results.append({"pmcid": item["pmcid"], "organism": organism})

            if results:
                await save_organism(engine, results)


if __name__ == '__main__':
    asyncio.run(main())
