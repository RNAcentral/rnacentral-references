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
import json
import os
import requests

from aiopg.sa import create_engine
from dotenv import load_dotenv

from consumer.settings import EUROPE_PMC
from database.results import get_all_pmcid, retracted_article

load_dotenv()


async def find_retracted_articles():
    """
    Function to find articles that have been retracted.
    Run it with: python3 find_retracted_articles.py
    :return: None
    """

    # get parameters
    user = os.getenv("username")
    database = os.getenv("db")
    host = os.getenv("host")
    password = os.getenv("pass")
    webhook = os.getenv("webhook")

    async with create_engine(user=user, database=database, host=host, password=password) as engine:
        # get list of articles
        pmcid_list = await get_all_pmcid(engine)

        # check 30 articles at a time
        step = 30
        for sublist in range(0, len(pmcid_list), step):
            check_pmcid = pmcid_list[sublist:sublist+step]

            # create json object
            obj = {"ids": []}
            for item in check_pmcid:
                obj["ids"].append({"src": "PMC", "extId": item})

            # use the Status Update Search module of the Europe PMC RESTful API
            data = requests.post(EUROPE_PMC + "status-update-search", json=obj).json()

            if "articlesWithStatusUpdate" in data and len(data["articlesWithStatusUpdate"]) > 0:
                for item in data["articlesWithStatusUpdate"]:
                    if "statusUpdates" in item and "RETRACTED" in item["statusUpdates"]:
                        # send a message on Slack
                        message = f'Article {item["extId"]} has been retracted'
                        requests.post(webhook, json.dumps({"text": message}))

                        # update article
                        await retracted_article(engine, item["extId"])

            await asyncio.sleep(0.3)


if __name__ == '__main__':
    asyncio.run(find_retracted_articles())
