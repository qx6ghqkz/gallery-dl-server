#!/usr/bin/env bash

check_etc () {
  if [[ ! -f "/etc/passwd" ]]; then
    exit 1
  fi
}

get_ids () {
  UID_OG="$(id -u appuser)"
  GID_OG="$(id -g appuser)"

  UID="${UID:-$UID_OG}"
  GID="${GID:-$GID_OG}"
}

set_umask () {
  UMASK="${UMASK:-022}"
  umask "$UMASK"
}

mod_ids () {
  groupmod --non-unique --gid "$GID" appgroup >/dev/null 2>&1
  usermod --non-unique --gid "$GID" --uid "$UID" appuser >/dev/null 2>&1

  chown -R "$UID:$GID" /usr/src/app >/dev/null 2>&1
}

init () {
  if [[ "$UID" -eq "$(id -u appuser)" && "$GID" -eq "$(id -g appuser)" ]]; then
    log 0
    if [[ "$(id -u)" -eq "$(id -u root)" ]]; then
      start 0
    elif [[ "$(id -u)" -eq "$(id -u appuser)" ]]; then
      start 1
    else
      exit 0
    fi
  else
    log 1
    if [[ "$(id -u)" -eq "$(id -u root)" ]]; then
      start 0
    elif [[ "$(id -u)" -eq "$(id -u appuser)" ]]; then
      start 1
    else
      exit 0
    fi
  fi
}

log() {
  local RESET="\033[0m"
  local GREEN="\033[0;32m"

  if [[ $1 -eq 0 ]]; then
    echo -e "${GREEN}INFO:${RESET}     Starting process with UID=$UID and GID=$GID ($(getent passwd $UID | cut -d: -f1))"
  elif [[ $1 -eq 1 ]]; then
    echo -e "${GREEN}INFO:${RESET}     Starting process with UID=$(id -u) and GID=$(id -g) ($(id -u -n))"
  else
    exit 0
  fi
}

start() {
  init_conf
  if [[ $1 -eq 0 ]]; then
    exec script -q -c "exec su-exec appuser python3 -m gallery_dl_server --port $CONTAINER_PORT" /dev/null
  elif [[ $1 -eq 1 ]]; then
    exec script -q -c "exec python3 -m gallery_dl_server --port $CONTAINER_PORT" /dev/null
  else
    exit 0
  fi
}

init_conf() {
  dir="/config"
  files=(
    "gallery-dl.conf"
    "gallery-dl.yaml"
    "gallery-dl.yml"
    "gallery-dl.toml"
    "config.json"
    "config.yaml"
    "config.yml"
    "config.toml"
  )

  if [[ -d "$dir" ]]; then
    rm -f "$dir/hosts" "$dir/hostname" "$dir/resolv.conf" >/dev/null 2>&1

    any_file_exists=false
    for file in "${files[@]}"; do
      if [[ -f "$dir/$file" ]]; then
        any_file_exists=true
        break
      fi
    done

    if ! $any_file_exists; then
      mv -n /usr/src/app/docs/gallery-dl.conf "$dir" >/dev/null 2>&1
    fi
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
set_umask
if [[ "$UID" -ne "$UID_OG" || "$GID" -ne "$GID_OG" ]]; then
  if [[ "$(id -u -n 2>/dev/null)" == "root" ]]; then
    mod_ids
    init
  elif [[ "$(id -u -n 2>/dev/null)" == "appuser" ]]; then
    init
  else
    exit 2
  fi
elif [[ "$(id -u -n 2>/dev/null)" == "root" ]]; then
  init
elif [[ "$(id -u -n 2>/dev/null)" == "appuser" ]]; then
  init
else
  exit 2
fi
