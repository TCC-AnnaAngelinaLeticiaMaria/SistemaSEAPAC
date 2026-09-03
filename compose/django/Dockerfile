# pull official base image
FROM python:3.11.3-slim-bullseye

# set work directory
WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install system dependencies
RUN apt-get update && apt-get install -y --fix-missing netcat
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        netcat \
        libglib2.0-0 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY ./compose/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./compose/django/start /app/start
RUN sed -i 's/\r$//g' /app/start
RUN chmod +x /app/start

# copy entrypoint.sh
#COPY ./entrypoint.sh .
#RUN sed -i 's/\r$//g' /usr/src/app/entrypoint.sh
#RUN chmod +x /usr/src/app/entrypoint.sh
# copy project
COPY . .

#CMD ["/app/start"]
# run entrypoint.sh
ENTRYPOINT ["bash","/entrypoint"]