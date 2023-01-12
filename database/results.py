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


async def get_pmid(engine, pmid):
    """
    Function to get article based on pmid
    :param engine: params to connect to the db
    :param pmid: id of the PM
    :return: pmcid
    """
    query = (sa.select([Article.c.pmcid]).select_from(Article).where(Article.c.pmid == pmid))  # noqa
    try:
        async with engine.acquire() as connection:
            async for row in connection.execute(query):
                return row.pmcid
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in get_pmid()") from e


async def get_job_results(engine, job_id):
    """
    Function to get job results
    :param engine: params to connect to the db
    :param job_id: id of the job
    :return: list of dicts containing the results
    """
    results = []
    output = []
    results_sql = (sa.select([Result.c.pmcid, Result.c.id_in_title, Result.c.id_in_abstract, Result.c.id_in_body])
                   .select_from(Result)
                   .where(Result.c.job_id == job_id))  # noqa

    try:
        async with engine.acquire() as connection:
            async for row in connection.execute(results_sql):
                # get results
                results.append({
                    'pmcid': row.pmcid,
                    'id_in_title': row.id_in_title,
                    'id_in_abstract': row.id_in_abstract,
                    'id_in_body': row.id_in_body
                })

            for result in results:
                article_sql = (sa.select([Article.c.title, Article.c.abstract, Article.c.author, Article.c.pmid,
                                          Article.c.doi, Article.c.year, Article.c.journal, Article.c.score,
                                          Article.c.cited_by, Article.c.retracted])
                               .select_from(Article)
                               .where(Article.c.pmcid == result['pmcid']))  # noqa
                async for row in connection.execute(article_sql):
                    # get article
                    output.append({
                        'job_id': job_id,
                        'pmcid': result['pmcid'],
                        'title': row.title,
                        'abstract': row.abstract,
                        'author': row.author,
                        'pmid': row.pmid,
                        'doi': row.doi,
                        'year': row.year,
                        'journal': row.journal,
                        'score': row.score,
                        'cited_by': row.cited_by,
                        'retracted': row.retracted,
                        'id_in_title': result['id_in_title'],
                        'id_in_abstract': result['id_in_abstract'],
                        'id_in_body': result['id_in_body'],
                    })

            return output

    except psycopg2.Error as e:
        raise DatabaseConnectionError(str(e)) from e


async def get_articles(engine):
    """
    Function to get the data that will be used by the search index
    :param engine: params to connect to the db
    :return: list of dicts containing articles
    """
    articles = []
    article_sql = (sa.select([Article.c.pmcid, Article.c.title, Article.c.abstract, Article.c.author, Article.c.pmid,
                              Article.c.doi, Article.c.year, Article.c.journal, Article.c.score, Article.c.cited_by])
                   .select_from(Article)
                   .where(~Article.c.retracted))  # noqa

    try:
        async with engine.acquire() as connection:
            async for row in connection.execute(article_sql):
                # get all articles
                articles.append({
                    'pmcid': row['pmcid'],
                    'title': row.title,
                    'abstract': row.abstract,
                    'author': row.author,
                    'pmid': row.pmid,
                    'doi': row.doi,
                    'year': str(row.year),
                    'journal': row.journal,
                    'score': str(row.score),
                    'cited_by': str(row.cited_by),
                })

            for article in articles:
                # get the results of each article
                results = []
                results_sql = (sa.select([Result.c.id, Result.c.job_id, Result.c.id_in_title, Result.c.id_in_abstract,
                                          Result.c.id_in_body])
                               .select_from(Result)
                               .where(Result.c.pmcid == article['pmcid']))  # noqa

                async for row in connection.execute(results_sql):
                    results.append({
                        'id': row.id,
                        'job_id': row.job_id,
                        'id_in_title': str(row.id_in_title),
                        'id_in_abstract': str(row.id_in_abstract),
                        'id_in_body': str(row.id_in_body)
                    })

                for result in results:
                    # get display_id
                    display_id = sa.select([Job.c.display_id]).select_from(Job).where(Job.c.job_id == result['job_id'])
                    async for row in connection.execute(display_id):
                        result['display_id'] = row.display_id

                    # get abstract sentence
                    abstract_sql = sa.text(
                        '''SELECT sentence FROM litscan_abstract_sentence 
                        WHERE result_id=:result_id ORDER BY length(sentence) DESC LIMIT 1'''
                    )
                    async for row in connection.execute(abstract_sql, result_id=result['id']):
                        result['abstract_sentence'] = row.sentence

                    # get body sentence
                    body_sql = sa.text(
                        '''SELECT sentence FROM litscan_body_sentence 
                        WHERE result_id=:result_id ORDER BY length(sentence) DESC LIMIT 1'''
                    )
                    async for row in connection.execute(body_sql, result_id=result['id']):
                        result['body_sentence'] = row.sentence

                article['result'] = results

                # check if this article was manually annotated for any URS
                manually_annotated = []
                manually_annotated_sql = (sa.select([ManuallyAnnotated.c.urs])
                                          .select_from(ManuallyAnnotated)
                                          .where(ManuallyAnnotated.c.pmcid == article['pmcid']))  # noqa

                async for row in connection.execute(manually_annotated_sql):
                    manually_annotated.append(row.urs.upper())

                article['manually_annotated'] = manually_annotated

                # get organism
                organisms = []
                organisms_sql = (sa.select([Organism.c.organism])
                                 .select_from(Organism)
                                 .where(Organism.c.pmcid == article['pmcid']))

                async for row in connection.execute(organisms_sql):
                    organisms.append(row.organism)

                organisms_names = []
                for organism in organisms:
                    name_sql = (sa.select([Taxonomy.c.name])
                                .select_from(Taxonomy)
                                .where(Taxonomy.c.id == organism))

                    async for row in connection.execute(name_sql):
                        organisms_names.append(row.name)

                article['organisms'] = organisms_names

            return articles

    except psycopg2.Error as e:
        raise DatabaseConnectionError(str(e)) from e


async def get_all_pmcid(engine):
    """
    Function to get all pmcid that were not retracted
    :param engine: params to connect to the db
    :return: list of pmcid
    """
    articles = []
    article_sql = (sa.select([Article.c.pmcid]).select_from(Article).where(~Article.c.retracted))  # noqa

    try:
        async with engine.acquire() as connection:
            async for row in connection.execute(article_sql):
                articles.append(row.pmcid)
            return articles
    except psycopg2.Error as e:
        raise DatabaseConnectionError(str(e)) from e


async def retracted_article(engine, pmcid):
    """
    Function to set article as retracted
    :param engine: params to connect to the db
    :param pmcid: article that was retracted
    :return: None
    """
    try:
        async with engine.acquire() as connection:
            try:
                query = sa.text('''UPDATE litscan_article SET retracted=:retracted WHERE pmcid=:pmcid''')
                await connection.execute(query, retracted=True, pmcid=pmcid)
            except Exception as e:
                logging.debug("Failed to retracted_article. Error: {}.".format(e))
    except psycopg2.Error as e:
        raise DatabaseConnectionError(str(e)) from e


async def get_all_pmid(engine):
    """
    Function to get articles that contain pmid
    :param engine: params to connect to the db
    :return: list of dicts containing articles
    """
    query = (sa.select([Article.c.pmcid, Article.c.pmid]).select_from(Article).where(Article.c.pmid != None))  # noqa
    pmid_list = []
    try:
        async with engine.acquire() as connection:
            async for row in connection.execute(query):
                pmid_list.append({"pmcid": row.pmcid, "pmid": row.pmid})
            return pmid_list
    except psycopg2.Error as e:
        raise DatabaseConnectionError("Failed to open DB connection in get_pmid()") from e
