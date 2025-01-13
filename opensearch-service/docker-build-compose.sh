#!/bin/bash
# Helper function for local development.
# Builds docker image and starts the image in one command


# Define NR key for local validation.
# Deployment to ECS will have these keys available in AWS
PASS=pass
export NEW_RELIC_LICENSE_KEY=`$PASS new-relic-license-key`

docker build . && docker compose up --remove-orphans -d
