FROM python:3.11-slim-bullseye

WORKDIR /app
COPY . .
RUN apt update
RUN apt install -y make tzdata libpq-dev gdal-bin libgdal-dev
RUN pip install --upgrade pip
RUN pip install pipenv
RUN pipenv install
EXPOSE 8000
CMD ["bash", "-c", "/app/run_service.sh"]
