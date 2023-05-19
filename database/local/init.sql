CREATE USER docker WITH ENCRYPTED PASSWORD 'example';
CREATE DATABASE reference;
GRANT ALL PRIVILEGES ON DATABASE reference TO docker;
ALTER DATABASE reference OWNER TO docker;
ALTER ROLE docker CREATEDB;
CREATE DATABASE test_reference;
GRANT ALL PRIVILEGES ON DATABASE test_reference TO docker;
ALTER DATABASE test_reference OWNER TO docker;
GRANT ALL ON schema public TO docker;
