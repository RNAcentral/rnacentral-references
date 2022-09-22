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
import random
import string
import sqlalchemy as sa

from aiopg.sa import create_engine
from dotenv import load_dotenv

from database.models import Article, Result

load_dotenv()


async def create_json_file(annotations):
    """
    Creates the Json file that will be used by Europe PMC
    :param annotations: list of results
    :return: none
    """
    # random string to use in filename
    random_char = "".join(random.choices(string.ascii_uppercase + string.digits, k=16))

    with open("json_files/" + "RNAcentral_annotations_" + random_char, "w", encoding="utf-8") as outfile:
        outfile.write("[" + ",\n".join(json.dumps(row, ensure_ascii=False) for row in annotations) + "]\n")


async def create_annotation(json_obj, exact, section, job_id, urs):
    """
    Function to add annotation
    :param json_obj: json object
    :param exact: sentence
    :param section: section from which the sentence was taken
    :param job_id: identifiers (ids), gene names or synonyms
    :param urs: URS related to the job_id
    :return: new annotation
    """
    return json_obj["anns"].append({
        "exact": exact,
        "section": section,
        "tags": [
            {
                "name": job_id,
                "uri": "https://rnacentral.org/rna/" + urs.upper()
            }
        ]
    })


async def export_results():
    """
    Function to export results to Europe PMC.
    Run it with: python3 export_results.py
    """

    # get parameters
    user = os.getenv("username")
    database = os.getenv("db")
    host = os.getenv("host")
    password = os.getenv("pass")

    # list of annotations
    annotations = []

    async with create_engine(user=user, database=database, host=host, password=password) as engine:
        # get list of articles
        query = (sa.select([Article.c.pmcid, Article.c.title]).select_from(Article).where(~Article.c.retracted))  # noqa
        pmcid_list = []

        async with engine.acquire() as connection:
            async for row in connection.execute(query):
                pmcid_list.append({"pmcid": row["pmcid"], "title": row["title"]})

            for item in pmcid_list:
                json_obj = {"src": "PMC", "id": item["pmcid"], "provider": "RNAcentral", "anns": []}

                # get results
                results = []
                results_sql = (sa.select([Result.c.id, Result.c.job_id, Result.c.id_in_title, Result.c.id_in_abstract,
                                    Result.c.id_in_body])
                               .select_from(Result)
                               .where(Result.c.pmcid == item["pmcid"]))  # noqa

                async for row in connection.execute(results_sql):
                    results.append({
                        "id": row["id"],
                        "job_id": row["job_id"],
                        "id_in_title": row["id_in_title"],
                        "id_in_abstract": row["id_in_abstract"],
                        "id_in_body": row["id_in_body"]
                    })

                # remove duplicate sentences for similar job_ids.
                # e.g. article PMC6157089 uses the following job_ids: 16s rrna, rrna, 16s
                # in this case we want to export only 16s rrna
                remove_jobs = []
                if len(results) > 1:
                    job_list = [item["job_id"] for item in results]

                    # check if any job_id contains two or more words
                    check_jobs = False
                    for job in job_list:
                        if len(job.split()) > 1:
                            check_jobs = True

                    # list of job_ids which should not be used
                    if check_jobs:
                        tmp_list = list(job_list)
                        for job in job_list:
                            tmp_list.remove(job)
                            if any(job in jobs for jobs in tmp_list):
                                remove_jobs.append(job)
                            tmp_list = list(job_list)

                # filter results
                results = [item for item in results if item["job_id"] not in remove_jobs]

                for result in results:
                    # get urs
                    urs_sql = sa.text(
                        '''SELECT primary_id FROM database
                        WHERE job_id=:job_id AND primary_id LIKE 'urs%' LIMIT 1'''
                    )
                    async for row in connection.execute(urs_sql, job_id=result["job_id"]):
                        result["urs"] = row.primary_id if row.primary_id else None

                    # add annotation in case the article title contains the job_id
                    if "urs" in result and result["id_in_title"]:
                        await create_annotation(json_obj, item["title"], "title", result["job_id"], result["urs"])

                    # add annotation if the abstract contains the job_id
                    if "urs" in result and result["id_in_abstract"]:
                        # get sentence in abstract
                        abstract_sql = sa.text(
                            '''SELECT sentence FROM abstract_sentence
                            WHERE result_id=:result_id ORDER BY length(sentence) DESC LIMIT 1'''
                        )
                        async for row in connection.execute(abstract_sql, result_id=result["id"]):
                            abs_sentence = row.sentence

                        if "found in an image, table or supplementary material" not in abs_sentence:
                            await create_annotation(json_obj, abs_sentence, "abstract", result["job_id"], result["urs"])

                    # add annotation if the body of the article contains the job_id
                    if "urs" in result and result["id_in_body"]:
                        # get sentence in body
                        body_sql = sa.text(
                            '''SELECT sentence FROM body_sentence
                            WHERE result_id=:result_id ORDER BY length(sentence) DESC LIMIT 1'''
                        )
                        async for row in connection.execute(body_sql, result_id=result["id"]):
                            body_sentence = row.sentence

                        if "found in an image, table or supplementary material" not in body_sentence:
                            await create_annotation(json_obj, body_sentence, "body", result["job_id"], result["urs"])

                if json_obj["anns"]:
                    # add annotation
                    annotations.append(json_obj)

    # every file must have less than 10000 rows, where each row represents an individual
    # article with all associated annotations.
    for i in range(0, len(annotations), 9999):
        await create_json_file(annotations[i:i + 9999])


if __name__ == "__main__":
    asyncio.run(export_results())
