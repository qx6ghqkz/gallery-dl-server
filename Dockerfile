#
# gallery-dl-server Dockerfile
#

FROM python:alpine

RUN apk add --no-cache \
  ffmpeg \
  tzdata

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt .
RUN apk --update-cache add --virtual build-dependencies gcc libc-dev make \
  && pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt \
  && apk del build-dependencies

COPY . .

ENV CONTAINER_PORT 9080

EXPOSE ${CONTAINER_PORT}

VOLUME ["/gallery-dl"]

RUN chmod +x ./start.sh

CMD ["./start.sh"]
