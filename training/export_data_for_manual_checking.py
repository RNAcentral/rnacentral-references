import asyncio
import csv
import json
import pandas as pd
import requests

from dotenv import load_dotenv
from export_data import clean_text, fetch_abstract
from typing import Any, Dict, List, Set

load_dotenv()

EUROPE_PMC: str = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
RATE_LIMIT: int = 8
ARTICLE_LIMIT: int = 20
EXCLUDED_KEYWORDS: List[str] = ["non-coding", "ncrna", "lncrna", "sncrna", "mirna"]


async def fetch_pmids(params: Dict[str, Any]) -> Set[str]:
    """Fetch PMIDs from Europe PMC based on query parameters."""
    pubmed_ids: Set[str] = set()

    try:
        response = requests.get(EUROPE_PMC, params=params)
        data = json.loads(response.text)
        results = data["resultList"]["result"]
    except (IndexError, KeyError, requests.RequestException):
        results = []

    for result in results:
        if "pmid" in result:
            pubmed_ids.add(result["pmid"])

    return pubmed_ids


async def process_abstracts(pmids: Set[str], semaphore: asyncio.Semaphore, rna_related: int) -> List[Dict[str, Any]]:
    """Fetch, clean, and classify abstracts based on RNA relation."""
    tasks = [fetch_abstract(pmid, semaphore) for pmid in pmids]
    abstracts = await asyncio.gather(*tasks)
    number_of_abstracts: int = 0
    processed: List[Dict[str, Any]] = []

    for abstract in filter(None, abstracts):
        cleaned_abstract = await clean_text(abstract)

        if rna_related == 0 and any(term in cleaned_abstract for term in EXCLUDED_KEYWORDS):
            continue
        elif rna_related == 1 and "non-coding" not in cleaned_abstract:
            continue
        elif "mrna" in cleaned_abstract and number_of_abstracts < ARTICLE_LIMIT:
            processed.append({"abstract": cleaned_abstract, "rna_related": rna_related})
            number_of_abstracts += 1
        elif number_of_abstracts >= ARTICLE_LIMIT:
            break

    return processed


async def main() -> None:
    """
    Collect abstracts from Europe PMC, process them, and save to a CSV file.
    These abstracts need to be manually reviewed.
    """
    list_of_abstracts: List[Dict[str, Any]] = []

    # use semaphore to fetch abstracts in parallel (respecting the API rate limit)
    semaphore = asyncio.Semaphore(RATE_LIMIT)

    queries: List[Dict[str, Any]] = [
        {
            "params": {
                "query": 'TITLE_ABS:"mrna" AND "ncrna" AND IN_EPMC:Y AND OPEN_ACCESS:Y AND NOT SRC:PPR',
                "format": "json",
                "sort_cited": "y",
                "pageSize": 100,
            },
            "rna_related": 1,
        },
        {
            "params": {
                "query": 'TITLE_ABS:"mrna" AND NOT ("ncrna" OR "rrna" OR "sncrna") AND IN_EPMC:Y AND OPEN_ACCESS:Y AND NOT SRC:PPR',
                "format": "json",
                "sort_cited": "y",
                "pageSize": 100,
            },
            "rna_related": 0,
        },
        # {
        #     "params": {
        #         "query": 'TITLE_ABS:"rna-seq" AND "ncrna" AND IN_EPMC:Y AND OPEN_ACCESS:Y AND NOT SRC:PPR',
        #         "format": "json",
        #         "sort_cited": "y",
        #         "pageSize": 100,
        #     },
        #     "rna_related": 1,
        # },
        # {
        #     "params": {
        #         "query": 'TITLE_ABS:"rna-seq" AND NOT ("ncrna" OR "rrna" OR "sncrna") AND IN_EPMC:Y AND OPEN_ACCESS:Y AND NOT SRC:PPR',
        #         "format": "json",
        #         "sort_cited": "y",
        #         "pageSize": 100,
        #     },
        #     "rna_related": 0,
        # },
    ]

    # pmids that mention "rna-seq" but may be unrelated to RNA
    # rna_seq_0 = {"25516281", "25605792", "25260700", "20979621", "28263959", "20132535", "28991892", "39606674",
    #              "26925227", "21796119"}

    # pmids that mention "rna-seq" and may be RNA-related
    # rna_seq_1 = {"32499815", "36395362", "28348640", "34681826", "29073095", "28195222", "32075098", "38832111",
    #              "38250806", "39494543"}

    for query in queries:
        pmids = await fetch_pmids(query["params"])
        abstracts = await process_abstracts(pmids, semaphore, query["rna_related"])
        list_of_abstracts.extend(abstracts)

    df = pd.DataFrame(list_of_abstracts)
    df.to_csv("check_abstracts.csv", mode="a", index=False, quoting=csv.QUOTE_NONNUMERIC)


if __name__ == "__main__":
    asyncio.run(main())
