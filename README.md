# RNAcentral References
This repository contains a simple API to explore [EuropePMC](https://europepmc.org/) articles. 

## Installation

###  Using docker-compose

1. `git clone https://github.com/RNAcentral/rnacentral-references.git`
2. `cd rnacentral-references`
3. create an `.env` file with the following environment variables (keep ENVIRONMENT=DOCKER and change LITSCAN_USER,
LITSCAN_PASSWORD and LITSCAN_DB as desired).
```
ENVIRONMENT=DOCKER
LITSCAN_USER=docker
LITSCAN_PASSWORD=example
LITSCAN_DB=reference
```
4. `docker-compose up --build`

A volume is being used to persist data generated by and used by Docker containers. 
If you want to recreate the database, just run the `docker-compose down --volumes` command before step 4. 

### Using local virtual environment

1. `git clone https://github.com/RNAcentral/rnacentral-references.git`
2. `cd rnacentral-references`
3. `python3 -m venv venv`
4. `source venv/bin/activate`
5. `pip3 install -r requirements.txt`
6. `docker build -t local-postgres database/local` - this will create an image with postgres databases.
7. `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres -t local-postgres` - this will create and start an 
instance of postgres on your local machine's 5432 port.
8. `python3 -m database` - creates necessary database tables
9. `python3 -m producer` - starts producer server on port 8080
10. `python3 -m consumer` - starts consumer server on port 8081

## How it works?

Submit a job using
```
curl -H "Content-Type:application/json" -d "{\"id\": \"RF00001\"}" localhost:8080/api/submit-job
```

This job will use the following query on EuropePMC:
```
query=("RF00001" AND ("rna" OR "mrna" OR "ncrna" OR "lncrna" OR "rrna" OR "sncrna") AND IN_EPMC:Y AND OPEN_ACCESS:Y AND NOT SRC:PPR)
```

Where:
1. `"RF00001"` is the string used in the search
2. `("rna" OR "mrna" OR "ncrna" OR "lncrna" OR "rrna" OR "sncrna")` is used to filter out possible false positives
3. `IN_EPMC:Y` means that the full text of the article is available in Europe PMC
4. `OPEN_ACCESS:Y` it must be an Open Access article to allow access to the full content
5. `NOT SRC:PPR` cannot be a Preprint, as preprints are not peer-reviewed

It is possible to change the query used to filter out possible false positives.
To do so, use the `query` parameter when submitting a job
```
curl -H "Content-Type:application/json" -d "{\"id\": \"RF00001\", \"query\": \"('foo' AND 'bar')\"}" localhost:8080/api/submit-job
```

Or if you don't want to use any queries, run
```
curl -H "Content-Type:application/json" -d "{\"id\": \"RF00001\", \"query\": \"\"}" localhost:8080/api/submit-job
```

You can check the results by accessing the URL
```
http://localhost:8080/api/results/rf00001
```
