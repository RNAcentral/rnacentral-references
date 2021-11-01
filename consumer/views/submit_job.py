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
import requests
import asyncio

from aiohttp import web
from aiojobs.aiohttp import spawn

from database.consumers import get_ip, set_consumer_status_and_job_id
from database.job import save_hit_count, set_job_status
from database.models import CONSUMER_STATUS_CHOICES, JOB_STATUS_CHOICES
from database.results import save_results
from textblob import TextBlob
from xml.etree import cElementTree as ET
from xml.etree.ElementTree import ParseError


# avoid messages of level=INFO from urllib3
logging.getLogger("urllib3").setLevel(logging.WARNING)


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
        logging.debug("Error getting data. Error message: {}".format(e))
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
    Use Europe PMC API to get data, search job_id within the article, save results,
    and make the consumer available for a new search.
    Note:
    - Europe PMC rate limits are 10 requests/second or 500 requests/minute.
    - The Europe PMC SOAP Web Service search results are sorted by relevance.
    :param consumer_ip: consumer IP address
    :param engine: params to connect to the db
    :param job_id: id of the job
    :return:
    """
    results = []
    start = datetime.datetime.now()
    regex = r"(^|\s|\()" + re.escape(job_id.split(":")[0]) + "($|[\s.,;?)])"
    europe_pmc = "https://www.ebi.ac.uk/europepmc/webservices/rest/"
    query = f'search?query=("{job_id}" AND "rna" AND IN_EPMC:Y AND OPEN_ACCESS:Y ' \
            f'AND NOT SRC:PPR)&pageSize=500&resultType=idlist'

    # fetch articles
    try:
        articles = requests.get(europe_pmc + query).text
    except requests.exceptions.RequestException as e:
        articles = None
        logging.debug("There was an error fetching articles from {}. "
                      "Error message: {} ".format(europe_pmc + query, e))

    root = None
    if articles:
        # parse using cElementTree
        try:
            root = ET.fromstring(articles)
        except ParseError:
            pass

    if root:
        # get pmcid
        pmcid_list = [
            item.find('pmcid').text for item in root.findall("./resultList/result") if item.find('pmcid') is not None
        ]

        # get hitCount
        try:
            hit_count = root.find('hitCount').text
        except AttributeError:
            hit_count = "-1"

    else:
        pmcid_list = None
        hit_count = "-1"

    if pmcid_list:
        for pmcid in pmcid_list:
            # wait a while to respect the rate limit
            await asyncio.sleep(0.3)

            # fetch full article
            try:
                get_article = requests.get(europe_pmc + pmcid + "/fullTextXML").text
            except requests.exceptions.RequestException as e:
                get_article = None
                logging.debug("There was an error fetching article {}. Error message: {} ".format(pmcid, e))

            if get_article:
                # parse using cElementTree
                try:
                    article = ET.fromstring(get_article)
                except ParseError as e:
                    article = None
                    logging.debug("There was an error parsing the article {}. Error message: {} ".format(pmcid, e))

                if article:
                    response = {}

                    # if the trans-title-group element is found it is because this article was not written in English
                    trans_title = article.find("./front/article-meta/title-group/trans-title-group")
                    if trans_title:
                        # decrease hit_count and skip the current iteration
                        hit_count = int(hit_count) - 1
                        continue

                    # get title
                    get_title = article.find("./front/article-meta/title-group/article-title")
                    title = ''.join(get_title.itertext()).strip()
                    response["title"] = title

                    # check if the title has the job_id
                    response["title_contains_value"] = False
                    title_blob = TextBlob(title)
                    for sentence in title_blob.sentences:
                        if re.search(regex, str(sentence.lower())):
                            response["title_contains_value"] = True
                            break

                    # check if the abstract has the job_id
                    get_abstract = article.findall(".//abstract//*")
                    for item in get_abstract:
                        if 'abstract' not in response and item.text:
                            item_blob = TextBlob(item.text)
                            for sentence in item_blob.sentences:
                                if re.search(regex, str(sentence.lower())):
                                    response["abstract"] = sentence.raw
                                    break

                    # check if the body has the job_id
                    get_body_p = article.findall(".//body//*")
                    for item in get_body_p:
                        if 'body' not in response and item.text:
                            item_blob = TextBlob(item.text)
                            for sentence in item_blob.sentences:
                                if re.search(regex, str(sentence.lower())):
                                    response["body"] = sentence.raw
                                    break

                    # get authors of the article
                    get_contrib_group = article.find("./front/article-meta/contrib-group")
                    response['author'] = ''

                    try:
                        get_authors = get_contrib_group.findall(".//name")
                        authors = []
                        for author in get_authors:
                            surname = author.find('surname').text if author.find('surname').text else ''
                            given_names = author.find('given-names').text if author.find('given-names').text else ''
                            if surname and given_names:
                                authors.append(surname + ", " + given_names)
                            elif surname or given_names:
                                authors.append(surname + given_names)
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

                    # get year
                    response["year"] = 0
                    get_year = article.findall("./front/article-meta/pub-date")
                    for item in get_year:
                        if item.attrib == {'pub-type': 'epub'}:
                            year = int(item.find('year').text) if item.find('year').text else 0
                            response["year"] = year

                    # get journal
                    response["journal"] = ''
                    get_journal = article.find("./front/journal-meta/journal-title-group/journal-title")
                    if get_journal and get_journal.text:
                        response["journal"] = get_journal.text
                    else:
                        # maybe it is in a different element
                        journal = article.find("./front/journal-meta/journal-title")
                        if journal and journal.text:
                            response["journal"] = journal.text

                    # add job_id
                    response["job_id"] = job_id

                    # add pmcid
                    response["pmcid"] = pmcid

                    # response must have abstract and body
                    if 'abstract' not in response:
                        response['abstract'] = ''

                    if 'body' not in response:
                        # check if there is a floats-group section
                        tables_and_fig = article.findall(".//floats-group//*")
                        for item in tables_and_fig:
                            if 'body' not in response and item.text:
                                item_blob = TextBlob(item.text)
                                for sentence in item_blob.sentences:
                                    if re.search(regex, str(sentence.lower())):
                                        response["body"] = sentence.raw + " (Id found in an image or table)"
                                        break

                    if 'body' not in response:
                        logging.debug("Job_id not found for pmcid {}.".format(pmcid))
                        response['body'] = ''

                    results.append(response)

    if results and int(hit_count) > 0:
        # save results in DB
        await save_results(engine, job_id, results)

        logging.debug("Saving {} result(s) in DB. Search performed in {} seconds".format(
            len(results), (datetime.datetime.now() - start).total_seconds())
        )

        # set job status
        await set_job_status(engine, job_id, status=JOB_STATUS_CHOICES.success)

    elif pmcid_list and not results:
        # if there is pmcid, there must be results
        logging.debug("Could not find job_id for {}.".format(pmcid_list))

        # set job status
        await set_job_status(engine, job_id, status=JOB_STATUS_CHOICES.error)

    elif not pmcid_list and int(hit_count) > 0:
        # if pmcid is not found, but hit_count is greater than 0, then something is wrong
        logging.debug("Could not get pmcid for job_id {}.".format(job_id))

        # set job status
        await set_job_status(engine, job_id, status=JOB_STATUS_CHOICES.error)

    elif not pmcid_list and int(hit_count) == 0:
        # if pmcid is not found and hit_count is 0, so no articles were actually found
        logging.debug("No results found for job_id {}.".format(job_id))

        # set job status
        await set_job_status(engine, job_id, status=JOB_STATUS_CHOICES.success)

    elif int(hit_count) == -1:
        # here the error could have been in the parse of the articles or in getting the hit_count
        logging.debug("Could not get hit_count for job_id {}.".format(job_id))
        logging.debug("Could not parse the articles {}.".format(articles))

        # set job status
        await set_job_status(engine, job_id, status=JOB_STATUS_CHOICES.error)

    # save hit_count
    if int(hit_count) > -1:
        await save_hit_count(engine, job_id, int(hit_count))

    # update consumer
    await set_consumer_status_and_job_id(engine, consumer_ip, CONSUMER_STATUS_CHOICES.available, "")
