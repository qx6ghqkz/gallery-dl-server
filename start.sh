#!/bin/sh
exec uvicorn gallery-dl-server:app --host 0.0.0.0 --port ${CONTAINER_PORT}
