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
import datetime
import logging
import re

from aiohttp import web
from aiojobs.aiohttp import spawn

from consumer.settings import path_to_xml_files
from database.consumers import get_ip, set_consumer_status_and_job_id
from database.job import set_job_status
from database.models import CONSUMER_STATUS_CHOICES, JOB_STATUS_CHOICES
from database.results import save_results
from textblob import TextBlob
from xml.etree import cElementTree as ET

logger = logging.Logger('aiohttp.web')


async def submit_job(request):
    """
    Function to change the necessary parameters and start the search
    :param request: params to connect to the db and info about the job
    :return: HTTP exception
    """
    # get the data
    try:
        data = await request.json()
        job_id = data['job_id']
        engine = request.app['engine']
        consumer_ip = get_ip(request.app)
        logging.debug("Submit job: consumer = {}, job_id = {}".format(consumer_ip, job_id))
    except (KeyError, TypeError, ValueError) as e:
        logger.error(e)
        raise web.HTTPBadRequest(text=str(e)) from e

    # update consumer
    await set_consumer_status_and_job_id(engine, consumer_ip, CONSUMER_STATUS_CHOICES.busy, job_id)

    # set job status
    await set_job_status(engine, job_id, status=JOB_STATUS_CHOICES.started)

    # spawn job in the background and return 201
    await spawn(request, seek_references(engine, job_id, consumer_ip))
    return web.HTTPCreated()


async def seek_references(engine, job_id, consumer_ip):
    """
    Function to get XML files, perform the search, save the results, and make the consumer available for a new search
    :param consumer_ip: consumer IP address
    :param engine: params to connect to the db
    :param job_id: id of the job
    :return:
    """
    results = []
    start = datetime.datetime.now()
    regex = r"(^|\s)" + re.escape(job_id) + "($|[\s.,?])"

    # list of xml files
    xml_files = [file for file in path_to_xml_files.glob('*.xml')]

    # read each of the xml files present in the files folder
    for file in xml_files:
        with open(file, "r") as f:
            read_data = f.read()

            # check if the file contains the job_id
            if re.search(regex, read_data.lower()):
                root = ET.fromstring(read_data)

                # check which article has the job_id
                for article in root.findall("./article"):
                    get_abstract = article.findall(".//abstract//p")
                    get_body = article.findall(".//body//p")
                    abstract_and_body = get_abstract + get_body
                    text = [item.text for item in abstract_and_body if item.text]

                    if re.search(regex, ' '.join(text).lower()):
                        response = {}

                        # check if the abstract has the job_id
                        for item in get_abstract:
                            if 'abstract' not in response:
                                try:
                                    item_blob = TextBlob(item.text)
                                    for sentence in item_blob.sentences:
                                        if re.search(regex, sentence.lower()):
                                            response["abstract"] = sentence.raw
                                            break
                                except TypeError:
                                    pass

                        # check if the body has the job_id
                        for item in get_body:
                            if 'body' not in response:
                                try:
                                    item_blob = TextBlob(item.text)
                                    for sentence in item_blob.sentences:
                                        if re.search(regex, sentence.lower()):
                                            response["body"] = sentence.raw
                                            break
                                except TypeError:
                                    pass

                        # get title
                        get_title = article.find("./front/article-meta/title-group/article-title")
                        title = ""
                        response["title_contains_value"] = False

                        # check if the title has the job_id
                        try:
                            title_blob = TextBlob(get_title.text)
                            for sentence in title_blob.sentences:
                                title = title + sentence.raw + " "
                                if re.search(regex, sentence.lower()):
                                    response["title_contains_value"] = True
                        except TypeError:
                            pass

                        response["title"] = title

                        # get authors of the article
                        get_contrib_group = article.find("./front/article-meta/contrib-group")
                        response['author'] = ''

                        try:
                            get_authors = get_contrib_group.findall(".//name")
                            authors = []
                            for author in get_authors:
                                surname = author.find('surname').text
                                given_names = author.find('given-names').text
                                authors.append(surname + ", " + given_names)
                            response["author"] = '; '.join(authors)
                        except AttributeError:
                            pass

                        # get pmid and doi
                        article_meta = article.findall("./front/article-meta/article-id")
                        response['doi'] = ''
                        response['pmid'] = ''

                        for item in article_meta:
                            if item.attrib == {'pub-id-type': 'doi'}:
                                response["doi"] = item.text
                            elif item.attrib == {'pub-id-type': 'pmid'}:
                                response["pmid"] = item.text

                        # add job_id
                        response["job_id"] = job_id

                        # response must have abstract and body
                        if 'abstract' not in response:
                            response['abstract'] = ''

                        if 'body' not in response:
                            response['body'] = ''

                        results.append(response)

    # save results in DB
    if results:
        await save_results(engine, job_id, results)
        logging.debug("Saving {} result(s) in DB. Search performed in {} seconds".format(
            len(results), (datetime.datetime.now() - start).total_seconds())
        )
    else:
        logging.debug("No article containing {} was found. Search performed in {} seconds".format(
            job_id, (datetime.datetime.now() - start).total_seconds())
        )

    # set job status
    await set_job_status(engine, job_id, status=JOB_STATUS_CHOICES.success)

    # update consumer
    await set_consumer_status_and_job_id(engine, consumer_ip, CONSUMER_STATUS_CHOICES.available, "")
