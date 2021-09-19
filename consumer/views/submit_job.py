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

from consumer.settings import PROJECT_ROOT
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

    # list of xml files
    path_to_xml_files = PROJECT_ROOT.parent / 'consumer' / 'files'
    xml_files = [file for file in path_to_xml_files.glob('*.xml')]

    # read each of the xml files present in the files folder
    for file in xml_files:
        # re.findall is faster than grep
        # command = ["/usr/bin/grep", "-o", "-m 1", "-w", "-iF", job_id, file]
        # output = subprocess.Popen(command, stdout=subprocess.PIPE).stdout.read()

        with open(file, "r") as f:
            read_data = f.read()

            # check if the file contains the job_id
            if re.findall(job_id, read_data.lower()):
                root = ET.fromstring(read_data)

                # check which article has the job_id
                for article in root.findall("./article"):
                    found_job_id = [
                        element for element in article.iter()
                        if element.text and re.findall(job_id, element.text.lower())
                    ]

                    # check if job_id is in title, abstract or body
                    if found_job_id:
                        get_id = get_ids_from_article(article, job_id)
                        if get_id:
                            results.append(get_id)

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


def contains_value(value, sentence):
    return f' {value} ' in f' {sentence} ' or f' {value},' in f' {sentence} ' or f' {value}.' in f' {sentence} '


def get_ids_from_article(article, value):
    """
    Search for the value in three different places: title, abstract, and body.
    :param article: article that will be used in the search
    :param value: string to search (job_id)
    :return: sentences of the article if the value is found, otherwise returns None
    """
    get_title = article.find("./front/article-meta/title-group/article-title")
    get_abstract = article.findall(".//abstract//p")
    get_body = article.findall(".//body//p")  # TODO: Maybe remove text from the intro?
    response = {}
    pattern_found = False

    if get_title:
        try:
            title_blob = TextBlob(get_title.text)
            for sentence in title_blob.sentences:
                if contains_value(value, sentence.lower()):
                    response["title"] = sentence.raw
                    pattern_found = True
        except TypeError:
            pass

    if get_abstract:
        # It is possible that the desired value is in several different sentences.
        # Just take the first one for now.
        pattern_found_in_abstract = False
        for item in get_abstract:
            if not pattern_found_in_abstract:
                try:
                    item_blob = TextBlob(item.text)
                    for sentence in item_blob.sentences:
                        if contains_value(value, sentence.lower()):
                            response["abstract"] = sentence.raw
                            pattern_found_in_abstract = True
                            pattern_found = True
                            break
                except TypeError:
                    pass

    if get_body:
        # It is possible that the desired value is in several different sentences.
        # Just take the first one for now.
        pattern_found_in_body = False
        for item in get_body:
            if not pattern_found_in_body:
                try:
                    item_blob = TextBlob(item.text)
                    for sentence in item_blob.sentences:
                        if contains_value(value, sentence.lower()):
                            response["body"] = sentence.raw
                            pattern_found_in_body = True
                            pattern_found = True
                            break
                except TypeError:
                    pass

    if pattern_found:
        # get authors of the article
        get_contrib_group = article.find("./front/article-meta/contrib-group")
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
        for item in article_meta:
            if item.attrib == {'pub-id-type': 'doi'}:
                response["doi"] = item.text
            elif item.attrib == {'pub-id-type': 'pmid'}:
                response["pmid"] = item.text

        # add job_id
        response["job_id"] = value

        # there must be title, abstract, body, author, pmid, doi, and job_id in response
        if 'title' not in response:
            response['title'] = ''

        if 'abstract' not in response:
            response['abstract'] = ''

        if 'body' not in response:
            response['body'] = ''

        if 'author' not in response:
            response['author'] = ''

        if 'doi' not in response:
            response['doi'] = ''

        if 'pmid' not in response:
            response['pmid'] = ''

    return response if response else None
