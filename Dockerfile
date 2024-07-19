#
# gallery-dl-server Dockerfile
#

FROM python:alpine

RUN apk add --no-cache \
  ffmpeg \
  tzdata

WORKDIR /usr/src/app

RUN python -m venv venv

ENV PATH="/usr/src/app/venv/bin:$PATH"

COPY requirements.txt .

RUN apk add --no-cache --virtual build-dependencies gcc libc-dev make \
  && pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt \
  && apk del build-dependencies

COPY . .

ENV CONTAINER_PORT=9080

EXPOSE $CONTAINER_PORT

VOLUME ["/gallery-dl"]

ENV USER=app
ENV GROUP=$USER
ENV UID=1000
ENV GID=$UID

RUN addgroup --gid "$GID" "$GROUP" \
  && adduser --disabled-password --gecos "" --home "$(pwd)" --ingroup "$GROUP" --no-create-home --uid "$UID" $USER

RUN mkdir -p /.cache/pip \
  && mkdir /.local

RUN chown -R $USER:$GROUP . \
  && chown -R $USER:$GROUP /.cache/pip \
  && chown -R $USER:$GROUP /.local

RUN chmod +x ./start.sh

USER $USER

CMD ["./start.sh"]
