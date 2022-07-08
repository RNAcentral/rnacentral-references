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
from database.job import get_hit_count, get_search_date, save_hit_count, set_job_status
from database.models import CONSUMER_STATUS_CHOICES, JOB_STATUS_CHOICES
from database.results import get_pmcid, get_pmcid_in_result, save_article, save_result, save_abstract_sentences, \
    save_body_sentences
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
    await set_consumer_status_and_job_id(engine, consumer_ip, CONSUMER_STATUS_CHOICES.busy, job_id.lower())

    # set job status
    await set_job_status(engine, job_id.lower(), status=JOB_STATUS_CHOICES.started)

    # get the last search date for this job_id, if any
    last_search = await get_search_date(engine, job_id.lower())
    last_search = last_search.date() if last_search else None

    # spawn job in the background and return 201
    await spawn(request, seek_references(engine, job_id, consumer_ip, last_search))
    return web.HTTPCreated()


async def articles_list(job_id, date, page="*"):
    """
    Function to create a list of "PMCIDs" that have job_id in their content
    :param job_id: id of the job
    :param date: search by date
    :param page: results page (* means the first page of results)
    :return: list of "PMCIDs" and the next page, if any
    """
    search_date = f' AND (FIRST_PDATE:[{date} TO {datetime.date.today().strftime("%Y-%m-%d")}])' if date else ''
    query = f'search?query=("{job_id}" AND ("rna" OR "mrna" OR "ncrna" OR "lncrna" OR "rrna" OR "sncrna") ' \
            f'AND IN_EPMC:Y AND OPEN_ACCESS:Y AND NOT SRC:PPR{search_date})&pageSize=500&cursorMark={page}'

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
        pmcid_list = []
        next_page = None

    return pmcid_list, next_page


async def seek_references(engine, job_id, consumer_ip, date):
    """
    Using the Europe PMC API, this function first gets a list of articles
    that mention job_id in their content and then parses article by article
    and tries to extract a sentence containing the job_id.
    Note:
    - Europe PMC rate limits are 10 requests/second or 500 requests/minute.
    - The Europe PMC SOAP Web Service search results are sorted by relevance.
    :param engine: params to connect to the db
    :param job_id: id of the job
    :param consumer_ip: consumer IP address
    :param date: last search date for this job_id
    :return: save the results in the database and make the consumer available for a new search
    """
    start = datetime.datetime.now()
    regex = r"(^|\s|\()" + re.escape(job_id.lower()) + "($|[\s.,;?)])"
    pmcid_list = []
    hit_count = 0

    temp_pmcid_list, next_page = await articles_list(job_id, date)
    for item in temp_pmcid_list:
        if item not in pmcid_list:
            pmcid_list.append(item)

    while next_page:
        temp_pmcid_list, next_page = await articles_list(job_id, date, next_page)
        for item in temp_pmcid_list:
            if item not in pmcid_list:
                pmcid_list.append(item)

    if date and pmcid_list:
        # filter pmcid_list to only search for articles/results that are not in the database
        pmcid_in_db = await get_pmcid_in_result(engine, job_id.lower())
        pmcid_list = [item for item in pmcid_list if item['pmcid'] not in pmcid_in_db]

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

            # remove tables, figures and supplementary material
            full_txt = re.sub(
                r"(?is)<(counts|table-wrap|table|fig-group|fig|supplementary-material).*?>.*?(</\1>)", "", get_article
            )

            # parse using ElementTree
            try:
                article = ET.fromstring(full_txt)
            except ParseError as e:
                article = None
                logging.debug("There was an error parsing the article {}. "
                              "Error message: {} ".format(element["pmcid"], e))

            if article:
                article_response = {}
                result_response = {}

                # if the trans-title-group element is found it is because this article was not written in English
                trans_title = article.find("./front/article-meta/title-group/trans-title-group")
                if trans_title:
                    # skip the current iteration
                    continue

                # get title
                get_title = article.find("./front/article-meta/title-group/article-title")
                try:
                    title = ''.join(get_title.itertext()).strip()
                    article_response["title"] = title
                except AttributeError:
                    # skip the current iteration
                    logging.debug("Title not found for pmcid {} and job_id {}".format(element["pmcid"], job_id))
                    continue

                # check if the title has the job_id
                result_response["id_in_title"] = True if job_id.lower() in title.lower() else False

                # get abstract
                get_abstract_tags = article.findall(".//abstract")
                abstract_types = ['teaser', 'web-summary', 'summary', 'precis', 'graphical', 'author-highlights']
                get_abstract_tags = [
                    item for item in get_abstract_tags if
                    not any(elem in item.attrib.values() for elem in abstract_types)
                ]
                abstract_text = [" ".join(item.itertext()) for item in get_abstract_tags]
                abstract = " ".join(abstract_text).replace(" .", ".").replace("  ", " ")
                article_response["abstract"] = abstract

                # check if the abstract has the job_id
                abstract_sentences = []
                for sentence in nltk.sent_tokenize(abstract):
                    if re.search(regex, sentence.lower()):
                        abstract_sentences.append(sentence)
                result_response["id_in_abstract"] = True if abstract_sentences else False

                # get body + all tags in it
                get_body_tags = article.findall(".//body//*")

                # common tags: 'sec', 'title', 'p', 'italic', 'bold', 'sup', 'sub', 'underline', 'sc', 'named-content',
                # 'list', 'list-item', 'uri', 'abbrev'

                # avoid text from the following tags as they result in bad sentences
                avoid_tags = [
                    'xref', 'ext-link', 'media', 'caption', 'monospace', 'label', 'disp-formula', 'inline-formula',
                    'inline-graphic', 'def', 'def-list', 'def-item', 'term', 'funding-source', 'award-id', 'graphic',
                    'alternatives', 'tex-math', 'sec-meta', 'kwd-group', 'kwd', 'object-id',
                    '{http://www.w3.org/1998/Math/MathML}math', '{http://www.w3.org/1998/Math/MathML}mrow',
                    '{http://www.w3.org/1998/Math/MathML}mi', '{http://www.w3.org/1998/Math/MathML}mo',
                    '{http://www.w3.org/1998/Math/MathML}msub', '{http://www.w3.org/1998/Math/MathML}mn',
                    '{http://www.w3.org/1998/Math/MathML}msup', '{http://www.w3.org/1998/Math/MathML}mtext',
                    '{http://www.w3.org/1998/Math/MathML}msubsup', '{http://www.w3.org/1998/Math/MathML}mover',
                    '{http://www.w3.org/1998/Math/MathML}mstyle', '{http://www.w3.org/1998/Math/MathML}munderover',
                    '{http://www.w3.org/1998/Math/MathML}mspace', '{http://www.w3.org/1998/Math/MathML}mfenced',
                    '{http://www.w3.org/1998/Math/MathML}mpadded', '{http://www.w3.org/1998/Math/MathML}mfrac',
                    '{http://www.w3.org/1998/Math/MathML}msqrt'
                ]
                get_body_tags = [
                    "".join(item.itertext()) for item in get_body_tags if item.text and item.tag not in avoid_tags
                ]

                # check if the body has the job_id
                body_sentences = []
                for item in get_body_tags:
                    for sentence in nltk.sent_tokenize(item):
                        if re.search(regex, sentence.lower()) and len(sentence.split()) > 3:
                            body_sentences.append(sentence)

                if abstract_sentences and not body_sentences:
                    result_response["id_in_body"] = False
                elif not abstract_sentences and not body_sentences:
                    result_response["id_in_body"] = True
                    body_sentences.append("%s found in an image, table or supplementary material" % job_id)
                else:
                    result_response["id_in_body"] = True

                # add job_id and pmcid
                result_response["job_id"] = job_id.lower()
                result_response["pmcid"] = element["pmcid"]

                # check if this article is already in the database
                article_in_db = await get_pmcid(engine, element["pmcid"])

                if not article_in_db:
                    # get authors of the article
                    get_contrib_group = article.find("./front/article-meta/contrib-group")
                    article_response['author'] = ''

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
                        article_response["author"] = '; '.join(authors)
                    except AttributeError:
                        pass

                    # get pmid and doi
                    article_meta = article.findall("./front/article-meta/article-id")
                    article_response['doi'] = ''
                    article_response['pmid'] = ''

                    for item in article_meta:
                        if item.attrib == {'pub-id-type': 'doi'}:
                            article_response["doi"] = item.text
                        elif item.attrib == {'pub-id-type': 'pmid'}:
                            article_response["pmid"] = item.text

                    # get year
                    article_response["year"] = 0
                    get_year = article.findall("./front/article-meta/pub-date")
                    pub_type = ['epub', 'ppub', 'pub']
                    for item in get_year:
                        if set(pub_type).intersection(item.attrib.values()):
                            year = int(item.find('year').text) if item.find('year').text else 0
                            article_response["year"] = year

                    # get journal
                    article_response["journal"] = ''
                    get_journal = article.find("./front/journal-meta/journal-title-group/journal-title")
                    try:
                        article_response["journal"] = get_journal.text
                    except AttributeError:
                        # maybe it is in a different element
                        journal = article.find("./front/journal-meta/journal-title")
                        try:
                            article_response["journal"] = journal.text
                        except AttributeError:
                            logging.debug("Journal not found for pmcid {}".format(element["pmcid"]))

                    # add pmcid
                    article_response["pmcid"] = element["pmcid"]

                    # add citation
                    article_response["cited_by"] = element["cited_by"]

                    # add score
                    article_response['score'] = len(abstract_sentences) + len(body_sentences)

                    # add retracted info
                    article_response['retracted'] = False

                    # save article
                    await save_article(engine, article_response)

                # save result
                result_id = await save_result(engine, result_response)

                # save abstract sentences
                abstract_sentences = [{"result_id": result_id, "sentence": item} for item in abstract_sentences]
                await save_abstract_sentences(engine, abstract_sentences)

                # save body sentences
                body_sentences = [{"result_id": result_id, "sentence": item} for item in body_sentences]
                await save_body_sentences(engine, body_sentences)

                hit_count += 1

    if hit_count > 0:
        logging.debug("Saving {} result(s) in DB. Search performed in {} seconds".format(
            str(hit_count), (datetime.datetime.now() - start).total_seconds())
        )

    elif not pmcid_list:
        # if pmcid is not found so no articles were actually found
        logging.debug("No results found for job_id {}.".format(job_id))

    # get hit_count if this search is to update a job_id
    if date:
        current_hit_count = await get_hit_count(engine, job_id.lower())
        hit_count = hit_count + current_hit_count

    # save hit_count
    await save_hit_count(engine, job_id.lower(), hit_count)

    # set job status
    await set_job_status(engine, job_id.lower(), status=JOB_STATUS_CHOICES.success)

    # update consumer
    await set_consumer_status_and_job_id(engine, consumer_ip, CONSUMER_STATUS_CHOICES.available, "")
