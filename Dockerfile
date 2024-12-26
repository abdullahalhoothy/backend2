# Use an official Python runtime as a parent image
FROM python:3.11-slim

ENV DATABASE_URL=postgresql://scraper_user:scraper_password@db:5432/aqar_scraper

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Update package lists and install git
RUN apt-get update && \
    apt-get install -y git


COPY . /app
EXPOSE 8000
CMD ["uvicorn", "run_apps:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
