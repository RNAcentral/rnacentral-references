FROM python:3.9-slim

RUN apt update && apt install -y gcc \
    && rm -fr /var/lib/apt/lists/*

# Set environment variables
ENV LITSCAN=/srv/litscan \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create folder
RUN mkdir -p $LITSCAN

# Create litscan user
RUN useradd -m -d /srv/litscan -s /bin/bash litscan

# Set work directory
WORKDIR $LITSCAN

# Copy requirements
COPY requirements.txt .

# Install requirements
RUN pip3 install --upgrade pip && pip3 install -r requirements.txt

# Copy and chown all files to the litscan user
COPY ../ .
RUN chown -R litscan:litscan /srv

# Set user
USER litscan

# Run producer
ENTRYPOINT python3 -m producer