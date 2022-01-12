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
import datetime
import logging
import nltk
import re
import requests

from aiohttp import web
from aiojobs.aiohttp import spawn

from consumer.settings import EUROPE_PMC
from database.consumers import get_ip, set_consumer_status_and_job_id
from database.job import save_hit_count, set_job_status
from database.models import CONSUMER_STATUS_CHOICES, JOB_STATUS_CHOICES
from database.results import save_results
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import ParseError


# avoid messages of level=INFO from urllib3
logging.getLogger("urllib3").setLevel(logging.WARNING)

# avoid messages of level=DEBUG for the module chardet.charsetprober
logging.getLogger('chardet.charsetprober').setLevel(logging.INFO)


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


async def articles_list(job_id, page="*"):
    """
    Function to create a list of "PMCIDs" that have job_id in their content
    :param job_id: id of the job
    :param page: results page (* means the first page of results)
    :return: list of "PMCIDs" and the next page, if any
    """
    query = f'search?query=("{job_id}" AND "rna" AND IN_EPMC:Y AND OPEN_ACCESS:Y ' \
            f'AND NOT SRC:PPR)&pageSize=500&cursorMark={page}'

    # fetch articles
    try:
        articles = requests.get(EUROPE_PMC + query).text
    except requests.exceptions.RequestException as e:
        articles = None
        logging.debug("There was an error fetching articles from {}. "
                      "Error message: {} ".format(EUROPE_PMC + query, e))

    root = None
    if articles:
        # parse using cElementTree
        try:
            root = ET.fromstring(articles)
        except ParseError:
            pass

    if root:
        # get pmcid and citation
        pmcid_list = [
            {"pmcid": item.find('pmcid').text, "cited_by": item.find('citedByCount').text}
            for item in root.findall("./resultList/result")
            if item.find('pmcid') is not None and item.find('citedByCount') is not None
        ]

        # get next page
        try:
            next_page = root.find('nextCursorMark').text
        except AttributeError:
            next_page = None
    else:
        pmcid_list = None
        next_page = None

    return pmcid_list, next_page


async def seek_references(engine, job_id, consumer_ip):
    """
    Using the Europe PMC API, this function first gets a list of articles
    that mention job_id in their content and then parses article by article
    and tries to extract a sentence containing the job_id.
    Note:
    - Europe PMC rate limits are 10 requests/second or 500 requests/minute.
    - The Europe PMC SOAP Web Service search results are sorted by relevance.
    :param consumer_ip: consumer IP address
    :param engine: params to connect to the db
    :param job_id: id of the job
    :return: save the results in the database and make the consumer available for a new search
    """
    results = []
    start = datetime.datetime.now()
    regex = r"(^|\s|\()" + re.escape(job_id.lower().split(":")[0]) + "($|[\s.,;?)])"
    pmcid_list = []
    hit_count = 0

    temp_pmcid_list, next_page = await articles_list(job_id)
    for item in temp_pmcid_list:
        if item not in pmcid_list:
            pmcid_list.append(item)

    while next_page:
        temp_pmcid_list, next_page = await articles_list(job_id, next_page)
        for item in temp_pmcid_list:
            if item not in pmcid_list:
                pmcid_list.append(item)

    for element in pmcid_list:
        # wait a while to respect the rate limit
        await asyncio.sleep(0.3)

        # fetch full article
        try:
            get_article = requests.get(EUROPE_PMC + element["pmcid"] + "/fullTextXML").text
        except requests.exceptions.RequestException as e:
            get_article = None
            logging.debug("There was an error fetching article {}. Error message: {} ".format(element["pmcid"], e))

        if get_article:
            # get text
            abstract_txt = re.search('<abstract(.*?)</abstract>', get_article, re.DOTALL)
            body_txt = re.search('<body(.*?)</body>', get_article, re.DOTALL)
            floats_group_txt = re.search('<floats-group(.*?)</floats-group>', get_article, re.DOTALL)

            if abstract_txt and body_txt and floats_group_txt:
                full_txt = abstract_txt[0] + body_txt[0] + floats_group_txt[0]
            elif abstract_txt and body_txt:
                full_txt = abstract_txt[0] + body_txt[0]
            elif body_txt:
                full_txt = body_txt[0]
            else:
                logging.debug("Text not found for pmcid {}.".format(element["pmcid"]))
                continue

            # remove tags
            full_txt_no_tags = re.sub('<[^>]*>', ' ', full_txt)

            # skip current iteration if job_id is not found
            if not re.search(regex, full_txt_no_tags.lower()):
                logging.debug("Job_id {} not found for pmcid {}.".format(job_id, element["pmcid"]))
                continue

            # remove tables and figures
            full_txt = re.sub(r"(?is)<(counts|table-wrap|table|fig-group|fig).*?>.*?(</\1>)", "", get_article)

            # parse using ElementTree
            try:
                article = ET.fromstring(full_txt)
            except ParseError as e:
                article = None
                logging.debug("There was an error parsing the article {}. "
                              "Error message: {} ".format(element["pmcid"], e))

            if article:
                response = {}

                # if the trans-title-group element is found it is because this article was not written in English
                trans_title = article.find("./front/article-meta/title-group/trans-title-group")
                if trans_title:
                    # skip the current iteration
                    continue

                # get title
                get_title = article.find("./front/article-meta/title-group/article-title")
                title = ''.join(get_title.itertext()).strip()
                response["title"] = title

                # check if the title has the job_id
                response["title_value"] = True if job_id.lower().split(":")[0] in title.lower() else False

                # check if the abstract has the job_id
                get_abstract_tags = article.findall(".//abstract//*")
                abstract_txt = ["".join(item.itertext()) for item in get_abstract_tags if item.text]
                abstract_txt = ". ".join(abstract_txt)
                abstract_txt = " ".join(abstract_txt.split())
                sentences = nltk.sent_tokenize(abstract_txt)
                abstract_sentences = [
                    sentence.replace("..", ".") for sentence in sentences
                    if re.search(regex, sentence.lower()) and len(sentence.split()) > 2
                ]
                response["abstract"] = str(max(abstract_sentences, key=len)) if abstract_sentences else ""
                response["abstract_value"] = True if abstract_sentences else False

                # check if the body has the job_id
                get_body_tags = article.findall(".//body//*")
                body_txt = ["".join(item.itertext()) for item in get_body_tags if item.text]
                body_txt = ". ".join(body_txt)
                body_txt = " ".join(body_txt.split())
                sentences = nltk.sent_tokenize(body_txt)
                body_sentences = [
                    sentence.replace("..", ".") for sentence in sentences
                    if re.search(regex, sentence.lower()) and len(sentence.split()) > 2
                ]
                body_sentences_filtered = [sentence for sentence in body_sentences if "(" not in sentence]

                if body_sentences_filtered:
                    response["body"] = str(max(body_sentences_filtered, key=len))
                elif body_sentences:
                    response["body"] = str(max(body_sentences, key=len))
                else:
                    response["body"] = job_id + " found in an image or table"

                response["body_value"] = True if response["body"] else False

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
                pub_type = ['epub', 'ppub', 'pub']
                for item in get_year:
                    if set(pub_type).intersection(item.attrib.values()):
                        year = int(item.find('year').text) if item.find('year').text else 0
                        response["year"] = year

                # get journal
                response["journal"] = ''
                get_journal = article.find("./front/journal-meta/journal-title-group/journal-title")
                try:
                    response["journal"] = get_journal.text
                except AttributeError:
                    # maybe it is in a different element
                    journal = article.find("./front/journal-meta/journal-title")
                    try:
                        response["journal"] = journal.text
                    except AttributeError:
                        logging.debug("Journal not found for pmcid {}".format(element["pmcid"]))

                # add job_id
                response["job_id"] = job_id

                # add pmcid
                response["pmcid"] = element["pmcid"]

                # add citation
                response["cited_by"] = element["cited_by"]

                # add score
                response['score'] = len(abstract_sentences) + len(body_sentences)

                hit_count += 1
                results.append(response)

    if results:
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

    elif not pmcid_list:
        # if pmcid is not found so no articles were actually found
        logging.debug("No results found for job_id {}.".format(job_id))

        # set job status
        await set_job_status(engine, job_id, status=JOB_STATUS_CHOICES.success)

    # save hit_count
    await save_hit_count(engine, job_id, hit_count)

    # update consumer
    await set_consumer_status_and_job_id(engine, consumer_ip, CONSUMER_STATUS_CHOICES.available, "")
