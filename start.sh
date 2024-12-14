#!/usr/bin/env bash

check_etc () {
  if [[ ! -f /etc/passwd ]]; then
    exit 1
  fi
}

get_ids () {
  UID_OG="$(id -u appuser)"
  GID_OG="$(id -g appuser)"

  UID="${UID:-$UID_OG}"
  GID="${GID:-$GID_OG}"
}

mod_ids () {
  groupmod --non-unique --gid "$GID" appgroup >/dev/null 2>&1
  usermod --non-unique --gid "$GID" --uid "$UID" appuser >/dev/null 2>&1

  chown --quiet -R "$UID:$GID" /usr/src/app /.cache/pip /.local
}

init () {
  if [[ $UID -eq $(id -u appuser) && $GID -eq $(id -g appuser) ]]; then
    log 0
    if [[ $(id -u) -eq $(id -u root) ]]; then
      start 0
    elif [[ $(id -u) -eq $(id -u appuser) ]]; then
      start 1
    else
      exit 0
    fi
  else
    log 1
    if [[ $(id -u) -eq $(id -u root) ]]; then
      start 0
    elif [[ $(id -u) -eq $(id -u appuser) ]]; then
      start 1
    else
      exit 0
    fi
  fi
}

log() {
  if [[ $1 -eq 0 ]]; then
    echo "INFO:     Starting process with UID=$UID and GID=$GID ($(getent passwd $UID | cut -d: -f1))"
  elif [[ $1 -eq 1 ]]; then
    echo "INFO:     Starting process with UID=$(id -u) and GID=$(id -g) ($(id -u -n))"
  else
    exit 0
  fi
}

start() {
  if [[ $1 -eq 0 ]]; then
    exec su-exec appuser uvicorn gallery-dl-server:app --host 0.0.0.0 --port "$CONTAINER_PORT" --log-level info --no-access-log
  elif [[ $1 -eq 1 ]]; then
    exec uvicorn gallery-dl-server:app --host 0.0.0.0 --port "$CONTAINER_PORT" --log-level info --no-access-log
  else
    exit 0
  fi
}

exit() {
  if [[ $1 -eq 0 ]]; then
    echo "error: fatal error"
  elif [[ $1 -eq 1 ]]; then
    echo "error: config mount location has changed from /etc to /config; please mount the directory containing gallery-dl.conf to /config" \
      "and make sure to update any paths specified inside your config file, e.g. /etc/cookies.txt --> /config/cookies.txt"
  elif [[ $1 -eq 2 ]]; then
    echo "error: invalid permissions; use the environment variables UID and GID to set the user ID and group ID" \
      "(defaults: UID=$UID_OG, GID=$GID_OG)"
  fi
  command exit 0
}

check_etc
get_ids
if [[ $UID -ne $UID_OG || $GID -ne $GID_OG ]]; then
  if [[ $(id -u -n 2>/dev/null) == root ]]; then
    mod_ids
    init
  elif [[ $(id -u -n 2>/dev/null) == appuser ]]; then
    init
  else
    exit 2
  fi
elif [[ $(id -u -n 2>/dev/null) == root ]]; then
  init
elif [[ $(id -u -n 2>/dev/null) == appuser ]]; then
  init
else
  exit 2
fi
