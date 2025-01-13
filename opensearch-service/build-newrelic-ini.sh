#!/bin/bash

## Note: this command depends on `gnu-sed` or `gsed` syntax rather than BSD `sed`
## `brew install gsed`
SED='sed'
if [[ "$(uname)" == "Darwin" ]]; then
    SED='gsed'
fi

cp newrelic.ini.template newrelic.ini
${SED} -i "s/NEW_RELIC_LICENSE_KEY_PLACEHOLDER/${NEW_RELIC_LICENSE_KEY}/g" newrelic.ini
