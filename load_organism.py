import asyncio
import csv
import os

from aiopg.sa import create_engine
from dotenv import load_dotenv
from database.organism import load_organism

load_dotenv()


async def main():
    """
    Load papers annotated with source organism.
    Data extracted from https://organisms.jensenlab.org
    :return: None
    """

    # get credentials
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DATABASE")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")

    csv.field_size_limit(500000000)  # 500 megabytes

    async with create_engine(user=user, password=password, database=database, host=host, port=port) as engine:
        with open("organism_textmining_mentions.tsv", "r") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter="\t")
            results = []
            for item in csv_reader:
                organism = item[0]
                pmid_list = list(map(int, item[1].split(" ")))
                for pmid in pmid_list:
                    results.append({"pmid": pmid, "organism": organism})
                await load_organism(engine, results)
                results = []


if __name__ == '__main__':
    asyncio.run(main())
