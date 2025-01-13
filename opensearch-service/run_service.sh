#!/bin/bash

./build-newrelic-ini.sh
# https://docs.gunicorn.org/en/stable/design.html#how-many-workers
# > we recommend (2 x $num_cores) + 1
# For 1 vCPU, we use 3 workers
pipenv run newrelic-admin run-program uvicorn main:app --host 0.0.0.0 --workers 3
