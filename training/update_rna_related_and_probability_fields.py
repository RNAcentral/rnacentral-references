import asyncio
import joblib
import os
import sqlalchemy as sa

from aiopg.sa import create_engine
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed

from export_data import clean_text

load_dotenv()


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def fetch_articles(connection, batch_size, offset):
    """
    Fetch articles from the database with retry mechanism.

    :param connection: database connection
    :param batch_size: number of articles to fetch
    :param offset: offset for pagination
    :return: list of articles
    """
    query = sa.text(
        '''SELECT pmcid, abstract 
           FROM litscan_article 
           WHERE NOT retracted
           ORDER BY pmcid 
           LIMIT :batch_size OFFSET :offset'''
    )
    result = await connection.execute(query, batch_size=batch_size, offset=offset)
    articles = await result.fetchall()
    return articles


async def is_rna_related(batch_size=1000):
    """
    Update the rna_related and probability fields of articles identified by LitScan

    :param batch_size: number of articles to fetch
    :return: None
    """
    # get credentials
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DATABASE")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")

    rna_pipeline = joblib.load("training/svc_pipeline.pkl")

    async with create_engine(user=user, database=database, host=host, password=password, port=port) as engine:
        async with engine.acquire() as connection:
            offset = 0

            while True:
                try:
                    articles = await fetch_articles(connection, batch_size, offset)
                except Exception as e:
                    print(f"Failed to fetch articles after 3 attempts. Error: {e}")
                    break

                if not articles:
                    break

                for article in articles:
                    pmcid = article["pmcid"]
                    abstract = await clean_text(article["abstract"])
                    relevance_label = rna_pipeline.predict([abstract])[0]
                    relevance_label = bool(int(relevance_label))
                    probability = rna_pipeline.predict_proba([abstract])[0][1]
                    probability = round(float(probability), 2)

                    try:
                        # update article data
                        update_query = sa.text(
                            '''UPDATE litscan_article 
                               SET rna_related = :rna_related, probability = :probability 
                               WHERE pmcid = :pmcid'''
                        )
                        await connection.execute(
                            update_query,
                            rna_related=relevance_label,
                            probability=probability,
                            pmcid=pmcid
                        )
                    except Exception as e:
                        print(f"Failed to save rna_related and probability for pmcid = {pmcid}. Error: {e}")

                # increment offset for the next batch
                offset += batch_size


if __name__ == "__main__":
    asyncio.run(is_rna_related())
