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
import logging
import psycopg2
import sqlalchemy as sa

from database import DatabaseConnectionError, SQLError
from database.models import Article, Result, AbstractSentence, BodySentence, Job, ManuallyAnnotated, Organism, Taxonomy


async def save_article(engine, result):
    """
    Function to save an article in the database
    :param engine: params to connect to the db
    :param result: dict containing the article
    :return: None
    """
    try:
        async with engine.acquire() as connection:
            try:
                await connection.execute(Article.insert().values(result))
            except Exception as e:
                logging.debug("Failed to save_article in the database. Error: {}.".format(e))
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in save_article, "
                                      "pmcid = %s" % result["pmcid"]) from e


async def save_result(engine, result):
    """
    Function to save result in the database
    :param engine: params to connect to the db
    :param result: dict containing the result
    :return: id of the result
    """
    try:
        async with engine.acquire() as connection:
            try:
                async for row in connection.execute(Result.insert().values(result).returning(Result.c.id)):
                    return row.id
            except Exception as e:
                logging.debug("Failed to save_result in the database. Error: {}.".format(e))
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in save_result, "
                                      "job_id = %s" % result["job_id"]) from e


async def save_abstract_sentences(engine, sentences):
    """
    Function to save abstract sentences in the database
    :param engine: params to connect to the db
    :param sentences: list of dicts containing the sentences
    :return: None
    """
    try:
        async with engine.acquire() as connection:
            try:
                await connection.execute(AbstractSentence.insert().values(sentences))
            except Exception as e:
                raise SQLError("Failed to save abstract sentences in the database") from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in save_abstract_sentences") from e


async def save_body_sentences(engine, sentences):
    """
    Function to save body sentences in the database
    :param engine: params to connect to the db
    :param sentences: list of dicts containing the sentences
    :return: None
    """
    try:
        async with engine.acquire() as connection:
            try:
                await connection.execute(BodySentence.insert().values(sentences))
            except Exception as e:
                raise SQLError("Failed to save body sentences in the database") from e
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in save_body_sentences") from e


async def get_pmcid(engine, pmcid):
    """
    Function to check if an article has already been saved in the database
    :param engine: params to connect to the db
    :param job_id: pmcid of the article
    :return: pmcid
    """
    query = (sa.select([Article.c.pmcid]).select_from(Article).where(Article.c.pmcid == pmcid))  # noqa
    try:
        async with engine.acquire() as connection:
            async for row in connection.execute(query):
                return row.pmcid
    except psycopg2.Error as e:
        raise DatabaseConnectionError(str(e)) from e


async def get_pmcid_in_result(engine, job_id):
    """
    Function to get pmcid from a given job_id
    :param engine: params to connect to the db
    :param job_id: id of the job
    :return: list of pmcid saved in db
    """
    try:
        async with engine.acquire() as connection:
            pmcid_in_db = []
            query = (sa.select([Result.c.pmcid]).select_from(Result).where(Result.c.job_id == job_id))
            async for row in connection.execute(query):
                pmcid_in_db.append(row.pmcid)
            return pmcid_in_db
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in get_pmcid_in_result()") from e


async def get_job_results(engine, job_id):
    """
    Function to get job results
    :param engine: params to connect to the db
    :param job_id: id of the job
    :return: list of dicts containing the results
    """
    results = []
    output = []

    try:
        async with engine.acquire() as connection:
            # get results
            results_sql = (sa.select([Result.c.id, Result.c.pmcid, Result.c.id_in_title, Result.c.id_in_abstract,
                                      Result.c.id_in_body])
                           .select_from(Result)
                           .where(Result.c.job_id == job_id)
                           .limit(100))  # noqa

            async for row in connection.execute(results_sql):
                results.append({
                    'id': row.id,
                    'pmcid': row.pmcid,
                    'id_in_title': row.id_in_title,
                    'id_in_abstract': row.id_in_abstract,
                    'id_in_body': row.id_in_body
                })

            for result in results:
                # get article
                article_sql = (sa.select([Article.c.title, Article.c.author, Article.c.pmid, Article.c.doi,
                                          Article.c.year, Article.c.journal, Article.c.score, Article.c.cited_by,
                                          Article.c.retracted])
                               .select_from(Article)
                               .where(Article.c.pmcid == result['pmcid']))  # noqa
                async for row in connection.execute(article_sql):
                    article = {
                        'title': row.title,
                        'author': row.author,
                        'pmid': row.pmid,
                        'doi': row.doi,
                        'year': row.year,
                        'journal': row.journal,
                        'score': row.score,
                        'cited_by': row.cited_by,
                        'retracted': row.retracted,
                    }

                # get abstract sentence
                abstract_sentence_list = []
                abstract_sql = sa.text(
                    '''SELECT sentence FROM litscan_abstract_sentence
                    WHERE result_id=:result_id'''
                )
                async for row in connection.execute(abstract_sql, result_id=result['id']):
                    abstract_sentence_list.append(row.sentence)

                # get body sentence
                body_sentence_list = []
                body_sql = sa.text(
                    '''SELECT location,sentence FROM litscan_body_sentence
                    WHERE result_id=:result_id ORDER BY location'''
                )
                async for row in connection.execute(body_sql, result_id=result['id']):
                    body_sentence_list.append({"location": row.location, "sentence": row.sentence})

                output.append({
                    'job_id': job_id,
                    'title': article['title'],
                    'author': article['author'],
                    'pmcid': result['pmcid'],
                    'pmid': article['pmid'],
                    'doi': article['doi'],
                    'year': article['year'],
                    'journal': article['journal'],
                    'score': article['score'],
                    'cited_by': article['cited_by'],
                    'retracted': article['retracted'],
                    'id_in_title': result['id_in_title'],
                    'id_in_abstract': result['id_in_abstract'],
                    'id_in_body': result['id_in_body'],
                    'abstract_sentence': abstract_sentence_list,
                    'body_sentence': body_sentence_list
                })

            return output

    except psycopg2.Error as e:
        raise DatabaseConnectionError(str(e)) from e
