#!/bin/bash
#
# test-dev.sh
#
# Author: Lain Musgrove (lain.proliant@gmail.com)
# Date: Monday November 6, 2023
#

PASS=pass
export NEW_RELIC_LICENSE_KEY=`$PASS new-relic-license-key`
export AWS_ACCESS_KEY_ID=`$PASS aws-lower-access-key-id`
export AWS_SECRET_ACCESS_KEY=`$PASS aws-lower-secret-access-key`
export AWS_PROFILE=mss_lower
export NEW_RELIC_CONFIG_FILE=newrelic.ini
export SALTED_BEARER_TOKEN_LIST=`$PASS mss-lower-salted-bearer-token-list`
#lower
export STAGE=desktop
export AWS_REGION=us-east-2
export OS_TEMP_PASSWORD=`$PASS open-search-cluster-dev-password-temp`
export OPEN_SEARCH_HOST=vpc-product-catalog-dev-se75f6j43alhucixxnxjq53tdq.us-east-2.es.amazonaws.com
export PRODUCTS_INDEX=products

export DEBUG=1

./build-newrelic-ini.sh

tempfile=`mktemp`
if ! pipenv install >$tempfile 2>$tempfile; then
    cat $tempfile
    rm $tempfile
    exit 1
fi
rm $tempfile

pipenv run newrelic-admin run-program uvicorn main:app --reload --host 0.0.0.0
