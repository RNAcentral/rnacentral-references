import gzip
import requests

from bs4 import BeautifulSoup
from flask import Flask
from flask import jsonify
from textblob import TextBlob
from xml.etree import cElementTree as ET

app = Flask(__name__)


@app.route("/")
def home():
    """
    This is just a simple page to say that you need to type something in the URL.
    Example: CFEOM1, PC12
    :return: info text
    """
    return 'Type something in the url, eg: http://127.0.0.1:5000/CFEOM1'


@app.route("/<value>")
def main(value):
    """
    This is the first step to create the reference widget. The main goal here is to test some tools.
    The search will only be done on some of the links available on the FTP server.
    :param value: string to search
    :return: json containing the articles that have the searched value
    """
    url = requests.get("https://europepmc.org/ftp/oa").text
    soup = BeautifulSoup(url, "html.parser")
    response = []

    for link in soup.find_all('a'):
        if link.get('href').startswith('PMC10'):
            data = "https://europepmc.org/ftp/oa/" + link.get('href')
            get_xml = requests.get(data)
            root = ET.fromstring(gzip.decompress(get_xml.content).decode("utf-8"))
            for article in root.findall("./article"):
                get_id = get_ids_from_article(article, value)
                if get_id:
                    response.append(get_id)

    return jsonify(response)


def get_ids_from_article(article, value):
    """
    Search for the value in three different places: title, abstract, and body.
    :param article: article that will be used in the search
    :param value: string to search
    :return: sentences of the article if the value is found, otherwise returns None
    """
    get_title = article.find("./front/article-meta/title-group/article-title")
    get_abstract = article.findall(".//abstract//p")
    get_body = article.findall(".//body//p")  # TODO: Maybe remove text from the intro?
    response = []
    pattern_found = False

    if get_title:
        try:
            title_blob = TextBlob(get_title.text)
            for sentence in title_blob.sentences:
                if value in sentence:
                    response.append({"title": sentence.raw})
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
                        if value in sentence:
                            response.append({"abstract": sentence.raw})
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
                        if value in sentence:
                            response.append({"body": sentence.raw})
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
            response.append({"authors": authors})
        except AttributeError:
            pass

        # get pmid and doi
        article_meta = article.findall("./front/article-meta/article-id")
        for item in article_meta:
            if item.attrib == {'pub-id-type': 'doi'}:
                response.append({"doi": item.text})
            elif item.attrib == {'pub-id-type': 'pmid'}:
                response.append({"pmid": item.text})

    return response if response else None
