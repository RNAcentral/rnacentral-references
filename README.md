# RNAcentral References
This repository contains the code to create the references used by RNAcentral. 
The goal is to access the Pubmed Central articles and search for specific ids. 

This is a project in progress. If you are interested in providing feedback 
please open an issue or pull request.

## Installation

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
