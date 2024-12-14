import asyncio
import csv
import json
import os
import pandas as pd
import re
import requests
import sqlalchemy as sa

from aiopg.sa import create_engine
from database.models import Article, ManuallyAnnotated
from dotenv import load_dotenv
from typing import Optional, List, Dict, Set

load_dotenv()

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
RATE_LIMIT = 8
NON_RNA_ARTICLE_LIMIT = 2300


async def clean_text(text: str) -> str:
    """
    Change abstract by removing HTML tags, URLs, content inside brackets,
    and extra whitespace, and converts it to lowercase.

    :param text: abstract text
    :return: cleaned text
    """
    text = text.lower()
    text = re.sub(r'<[^>]*>', " ", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def fetch_abstract(pmid: str, semaphore: asyncio.Semaphore) -> Optional[str]:
    """
    Fetches the abstract for a given PubMed ID (PMID) using the Europe PMC API.

    :param pmid: the PubMed ID
    :param semaphore: semaphore to enforce rate limiting
    :return: the abstract text if found, otherwise None.
    """
    async with semaphore:
        try:
            response = requests.get(
                f"{EUROPE_PMC}/search?query=EXT_ID:{pmid}"
                f"&resulttype=core&format=json"
            )
            response.raise_for_status()
            data = json.loads(response.text)
            return data["resultList"]["result"][0]["abstractText"]
        except (IndexError, KeyError, requests.RequestException):
            pass


async def tarbase_articles() -> Set[str]:
    """
    Retrieves PubMed IDs (PMIDs) from TarBase files. PMIDs are being extracted from:
    https://dianalab.e-ce.uth.gr/tarbasev9/downloads

    :return: a set of PMIDs found in TarBase
    """
    files = os.listdir("tarbase")
    pubmed_ids = set()

    for file in files:
        file_path = os.path.join("tarbase", file)
        if os.path.isfile(file_path):

            try:
                with open(file_path, "r") as tsvfile:
                    reader = csv.reader(tsvfile, delimiter="\t")
                    next(reader, None)  # skip header
                    pubmed_ids.update(line[16].strip() for line in reader if line[16].strip())
            except FileNotFoundError:
                print(f"Error: File '{file_path}' not found.")
            except Exception as e:
                print(f"An error occurred: {e}")

    return pubmed_ids


async def rfam_articles() -> Set[str]:
    """
    Retrieves PubMed IDs (PMIDs) from Rfam files. PMIDs are being extracted from:
    https://ftp.ebi.ac.uk/pub/databases/Rfam/15.0/Rfam.seed.gz

    :return: a set of PMIDs found in Rfam files
    """
    pubmed_ids = set()
    pattern = r"PMID:(\d+)"

    with open("rfam/Rfam.seed", "r", encoding="UTF-8", errors="ignore") as file:
        for line in file:
            matches = re.findall(pattern, line)
            if matches:
                pubmed_ids.add(matches[0])

    return pubmed_ids


async def manually_annotated_articles(pmids: Set[str]) -> List[Dict[str, int]]:
    """
    Retrieves manually annotated articles from the database, excluding those with PubMed IDs
    present in the provided `pmids` set.

    :param pmids: a set of PubMed IDs to exclude from the results
    :return: a list of abstracts that were manually annotated
    """
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DATABASE")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")

    offset = 0
    limit = 1000
    results = []

    while True:
        async with create_engine(user=user, database=database, host=host, password=password, port=port) as engine:
            subquery = sa.select([ManuallyAnnotated.c.pmcid]).distinct()
            query = (
                sa.select([Article.c.abstract])
                .select_from(Article)
                .where(
                    ~Article.c.retracted,
                    Article.c.abstract.isnot(None),
                    Article.c.abstract != "",
                    Article.c.pmcid.in_(subquery),
                    Article.c.pmid.notin_(pmids)
                )
                .limit(limit)
                .offset(offset)
            )  # noqa

            async with engine.acquire() as connection:
                get_data = await connection.execute(query)
                rows = await get_data.fetchall()

                if not rows:
                    break

                for row in rows:
                    abstract = await clean_text(row.abstract)
                    if "rna" in abstract:
                        results.append({"abstract": abstract, "rna_related": 1})

            offset += limit

    return results


async def non_rna_articles(page):
    pubmed_ids = set()
    query = f'/search?query=(IN_EPMC:Y AND OPEN_ACCESS:Y AND NOT SRC:PPR AND NOT "rna" ' \
            f'AND NOT "mrna" AND NOT "ncrna" AND NOT "lncrna" AND NOT "rrna" AND NOT "sncrna") ' \
            f'&sort_cited:y&pageSize=500&cursorMark={page}&format=json'

    try:
        response = requests.get(EUROPE_PMC + query)
        response.raise_for_status()
        data = json.loads(response.text)
        results = data["resultList"]["result"]
        next_page = data["nextCursorMark"]
        pubmed_ids.update(result["pmid"] for result in results if result["pmid"])
    except (IndexError, KeyError, requests.RequestException):
        next_page = None

    return pubmed_ids, next_page


async def main():
    """
    Main function to collect abstracts from various sources, clean them,
    and save the data to a CSV file.
    """
    list_of_abstracts = []

    # use semaphore to fetch abstracts in parallel (respecting the API rate limit)
    semaphore = asyncio.Semaphore(RATE_LIMIT)

    # get abstracts from TarBase and Rfam
    tarbase, rfam = await asyncio.gather(
        tarbase_articles(),
        rfam_articles()
    )
    tarbase_rfam_pmids = tarbase | rfam
    tarbase_rfam_task = [fetch_abstract(pmid, semaphore) for pmid in tarbase_rfam_pmids]
    tarbase_rfam_abstracts = await asyncio.gather(*tarbase_rfam_task)

    for abstract in filter(None, tarbase_rfam_abstracts):
        cleaned_abstract = await clean_text(abstract)
        list_of_abstracts.append({"abstract": cleaned_abstract, "rna_related": 1})

    # get non-rna related abstracts
    non_rna_pmids = set()
    next_page = "*"
    while len(non_rna_pmids) < NON_RNA_ARTICLE_LIMIT and next_page:
        tmp_pmids, next_page = await non_rna_articles(next_page)
        for pmid in tmp_pmids:
            if len(non_rna_pmids) < NON_RNA_ARTICLE_LIMIT:
                non_rna_pmids.add(pmid)

    non_rna_task = [fetch_abstract(pmid, semaphore) for pmid in non_rna_pmids]
    non_rna_abstracts = await asyncio.gather(*non_rna_task)

    for abstract in filter(None, non_rna_abstracts):
        cleaned_abstract = await clean_text(abstract)
        list_of_abstracts.append({"abstract": cleaned_abstract, "rna_related": 0})

    # get abstracts of manually annotated articles (extracted from the RNAcentral database)
    manually_annotated = await manually_annotated_articles(tarbase_rfam_pmids)

    # save to CSV
    df = pd.DataFrame(manually_annotated + list_of_abstracts)
    df.to_csv("data.csv", mode="a", index=False, quoting=csv.QUOTE_NONNUMERIC)


if __name__ == "__main__":
    asyncio.run(main())
