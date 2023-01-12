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
import gzip
import os
import random
import string
import xml.etree.ElementTree as ET


from aiopg.sa import create_engine
from dotenv import load_dotenv

from database.results import get_articles
from producer.settings import path_to_xml_files

load_dotenv()


async def create_xml_file(results):
    """
    Creates the XML that will be used by the search index
    :param results: list of results
    :return: None
    """
    # start to create a XML file
    database = ET.Element("database")
    ET.SubElement(database, "name").text = "RNAcentral"
    entries = ET.SubElement(database, "entries")

    for item in results:
        for elem in item['result']:
            entry = ET.SubElement(entries, "entry", id=elem["job_id"] + "_" + item['pmcid'])
            additional_fields = ET.SubElement(entry, "additional_fields")
            ET.SubElement(additional_fields, "field", name="entry_type").text = "Publication"
            ET.SubElement(additional_fields, "field", name="pmcid").text = item['pmcid']
            ET.SubElement(additional_fields, "field", name="title").text = item['title']
            ET.SubElement(additional_fields, "field", name="abstract").text = item['abstract']
            ET.SubElement(additional_fields, "field", name="author").text = item['author']
            ET.SubElement(additional_fields, "field", name="pmid").text = item['pmid']
            ET.SubElement(additional_fields, "field", name="doi").text = item['doi']
            ET.SubElement(additional_fields, "field", name="journal").text = item['journal']
            ET.SubElement(additional_fields, "field", name="year").text = item['year']
            ET.SubElement(additional_fields, "field", name="score").text = item['score']
            ET.SubElement(additional_fields, "field", name="cited_by").text = item['cited_by']
            ET.SubElement(additional_fields, "field", name="job_id").text = elem["display_id"]
            ET.SubElement(additional_fields, "field", name="title_value").text = elem['id_in_title']
            ET.SubElement(additional_fields, "field", name="abstract_value").text = elem['id_in_abstract']
            ET.SubElement(additional_fields, "field", name="body_value").text = elem['id_in_body']
            if 'abstract_sentence' in elem:
                ET.SubElement(additional_fields, "field", name="abstract_sentence").text = elem['abstract_sentence']
            if 'body_sentence' in elem:
                ET.SubElement(additional_fields, "field", name="body_sentence").text = elem['body_sentence']
            if 'manually_annotated' in item:
                for urs in item['manually_annotated']:
                    ET.SubElement(additional_fields, "field", name="manually_annotated").text = urs
            if 'organisms' in item:
                for organism in item['organisms']:
                    ET.SubElement(additional_fields, "field", name="organism").text = organism

    ET.SubElement(database, "entry_count").text = str(len(results))

    # save the file
    tree = ET.ElementTree(database)
    ET.indent(tree, space="\t", level=0)
    name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
    with gzip.open(str(path_to_xml_files) + "/publications_" + name + ".xml.gz", "wb") as file:
        tree.write(file)


async def search_index():
    """
    This function fetches the data of all articles.
    It calls the create_xml_file function every 10000 articles.
    Run it with: python3 search_index.py
    :return: create xml file
    """
    # get credentials
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DATABASE")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")

    async with create_engine(user=user, database=database, host=host, password=password, port=port) as engine:
        # get articles
        articles = await get_articles(engine)

        # create directory to store xml files, if necessary
        path_to_xml_files.mkdir(parents=True, exist_ok=True)

        for i in range(0, len(articles), 50000):
            await create_xml_file(articles[i:i + 50000])


if __name__ == '__main__':
    asyncio.run(search_index())
