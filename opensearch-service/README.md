# Marketplace Search Service
Marketplace Search Service (MSS) is part of the [ECM Search project](https://thetower.atlassian.net/wiki/x/WACQ3w) and
supports search queries and facet generation for FastStore, based on data stored in an
OpenSearch cluster.  MSS is implemented as a Python service using [FastAPI](https://fastapi.tiangolo.com/)
to handle the webservice infrastructure.

MSS has 3 search routes:
* `/products` - for querying for products and their skus
* `/facets` - for querying for facets (refinements of a search, such as brand or productType)
* `/product_detail` - for fetching the product for a specific product id or sku id
And 2 admin routes:
* `/ping` - for ALB health checks
* `/` - for current configuration of stage, product index, and OS host; authorization required call

Each route handles request parameters and creates response objects like VTEX's Intelligent Search to support backwards
compatibility for FastStore.  While MSS doesn't have an explicit interface, [this Confluence doc](https://thetower.atlassian.net/wiki/spaces/ECM/pages/3759308863/ECM+Search+-+FastStore+Interface+Definition)
attempts to capture the important aspects of the requests and responses.

The OpenSearch products index has distinct documents per {`productId` x `skuId` x `tradePolicy`}.  Any sku that exists
in multiple trade policies will have nearly identical documents for each trade policy with minor differences by storefront,
like image urls (which should have the account name in the domain) and frontend taxonomy categories (which can differ by
storefront).

The products index also has a synonyms analyzer called `global_product_synonyms`.  It is referenced as the analyzer for
any query that includes a text query.  This analyzer, and any future analyzers, must exist on the products index before
referencing them in the query, else the query will throw an error.

## File Organization
* `main.py` - The core request handling, including parameter parsing and defaults
* `search/`
  * `search/OSearch/` - Python files copied from [Events Service](https://github.com/Hearst-E-Commerce-Tech/events-service/tree/main)'s OSearch library
  * `search/base_products_query.py` - Base class that encapsulates a product query to apply filters and paginiation
  * `search/products_query.py` - Subclass that fetches the fields necessary for building product results
  * `search/facets_query.py` - Subclass that builds multiple facet queries (when necessary) and aggregations for building facet results
  * `search/sku_to_product_id_query.py` - Standalone for matching sku ids onto product ids (used for `product_detail` route)
* `converter/` - Helper functions for processing each OS query's response object into an Intelligent Search-shaped response object
* `.aws/` - ECS task definitions for QA and Prod
* `.github/` - GHA workflow definitions
* `auth/` - Bearer token authorization
* `constants/facets.py` - Hardcoded enums and facet metadata, including references into the OS documents
* `test-dev.sh` - Dev script to run the service locally on port 8000
* `ecr-push.sh` and `ech-deploy-dev.sh` - Dev-initiated push of the current code into ECR and ECS for MSS Dev
* `bcrypt_tokens.py`- Helper CLI for creating/salting tokens with bcrypt
* `schema.py` - Prototype code for converting a Product Change Snapshot into the OS product document; not part of the service

## New Relic
MSS Prod log search in NR: https://onenr.io/0qwLW7dmbQ5
MSS Prod dashboard: https://onenr.io/0yw401pm0w3
ECM Search Stack Prod: https://onenr.io/0yw401pm0w3

## Getting Started

### Setup
1. `pipenv install`
2. Setup `pre-commit`
   1. `brew install pre-commit`
   2. `pre-commit install`
3. Setup [passwordstore](https://www.passwordstore.org/)
   1. [Make a GPG password](https://www.digitalocean.com/community/tutorials/how-to-use-gpg-to-encrypt-and-sign-messages#set-up-gpg-keys) with `gpg --gen-key`
      1. Memorize your private key when generating the GPG password.  You'll need it when starting the service for local development.
   2. Record the key id for your generated GPG key
   3. `brew install pass` to install password store
   4. `pass init GPG_KEY_ID` using the previously generated key
4. Save critical passwords
   1. `pass add new-relic-license-key` with the NR backend license key
   2. `pass add aws-lower-access-key-id` with the AWS Access Key Id for the lower environment
   3. `pass add aws-lower-secret-access-key` with the AWS Secret Access Key for the lower environment
   4. `pass add open-search-cluster-dev-password-temp` with the OS Cluster master password for the lower environment
5. Configure environment variables
   1. `export NEW_RELIC_CONFIG_FILE=newrelic.ini`

### Run tests locally
Run `pytest` to running all unit tests in this repo
Run `pytest tests/*.py` to run a specific set of unit tests

### Start local instance
Run `./test-dev.sh` to initialize the service running locally, listening on port 8000, and auto-restart when files change.

### Deploy to MSS Dev
1. `./ecr-push.sh` to push Docker image to AWS ECR (Dev: https://us-east-2.console.aws.amazon.com/ecr/repositories/private/086408084823/marketplace-search-service?region=us-east-2)
2. `./ecr-deploy-dev.sh` to redeploy the ECS service with the image pushed in the previous step.

### Validate docker build
1. If on MacOS, run `brew install gnu-sed`
2. Shutdown other instances (`./test-dev.sh`) of server
3. Run `docker-build-compose.sh` which runs both of these commands
   1. `docker build .`
   2. `docker-compose up --remove-orphans -d`

## AWS
MSS runs in ECS clusters with an ALB providing a public-facing endpoint (accessible via VTEX) and horizontal scaling with
CNAME aliases for `marketplace-search.{dev|qa|prod}.ecmsvcs.com`.

### Parameters and Secrets
Environment variables and secrets are passed into MSS as defined in the task definitions for
[QA](.aws/ecs-task-definition-qa.json) and [Prod](.aws/ecs-task-definition-prod.json), and in the manually created dev
task definition.

The critical values that control MSS are:
* `STAGE` (environment) - passed to logging to filter events by dev vs QA vs prod
* `PRODUCTS_INDEX` (environment) - the OS index for products, generally set to `products`; for local dev testing,
override to `products_prod` a separate index for testing queries against real data
* `OPEN_SEARCH_HOST` (secret) - the OS host, treating it as a secret as it is open to the internet

### Synonym Management
OpenSearch on AWS supports synonym files as installed "packages" that are associated with analyzers.  To update the
synonyms file in prod:
1. Upload the file to https://us-east-2.console.aws.amazon.com/s3/buckets/marketplace-search-service-prod?prefix=synonyms/&region=us-east-2&bucketType=general
  * Currently, we're overwriting the `synonyms.txt` file
2. Copy the S3 URI (`s3://marketplace-search-service-prod/synonyms/synonyms.txt`)
3. Go to the Package (https://us-east-2.console.aws.amazon.com/aos/home?region=us-east-2#opensearch/custom-packages/F80613932)
4. Click "Update", paste the S3 URI into the "Package source" field, and click "Update package"
5. On the Package page, select the `product-catalog` domain, click "Apply update", and acknowledge the modal.
6. ???
7. Profit!  Wait a few minutes for the synonyms to update.

From the OS cluster dev tools console, you can test the analyzer:
```http request
GET products/_analyze
{
  "analyzer": "global_product_synonyms",
  "text": "sweater"
}
```


### AWS Setup Steps for Dev
These are the one-time steps taken to configure MSS Dev.  For QA and Prod stages, Github Actions manages the deployments.
See the workflow steps for .

1. Login to the AWS Lower instance
2. Create ECR repository
3. Create Secrets/Parameters: https://us-east-2.console.aws.amazon.com/systems-manager/parameters/?region=us-east-2&tab=Table
4. Create ECS Task Definition (refers to ECR repo and Secrets)
   1. Drop any fields that the JSON editor says are not allowed (because they are computed later)
5. Create ECS Service: https://us-east-2.console.aws.amazon.com/ecs/v2/clusters/ecm-development/services?region=us-east-2
6. Deploy newest version: https://us-east-2.console.aws.amazon.com/ecs/v2/clusters/ecm-development/services/marketplace-search-service-dev/update?region=us-east-2
   1. Select "Force new deployment" to grab properly tagged image

## Bearer tokens
> [!WARNING]
> As of June 2024, bearer tokens are only used to fetch configuration in the root route (`/`).  This section is retained
> in case we want to re-enable it in the future.

MSS uses bcrypt for authentication of bearer tokens.  Bearer tokens are stored in AWS Parameter
Store `marketplace-search-service-{stage}-bearer-token-list` for admin purposes (ie shared store to copy for clients).
MSS requires bearer auth tokens on all non-ping requests.  A comma-separated
list of salted tokens are passed in as the environment parameter `SALTED_BEARER_TOKEN_LIST` from the parameter store
in the parameter `marketplace-search-service-{stage}-salted-bearer-token-list`.  MSS never stores the unsalted
bearer token.  It uses bcrypt to compare the request's bearer token against each element of the salted token list,
requiring a match against any of the tokens.  Validation is performed in `auth/bearer_token_auth.py`

To generate a new bearer token and salt run `pipenv run python bearer_tokens.py`.  Optionally you can add parameters of
existing bearer tokens to generate new salted bearer tokens.  Copy the new token and salt into the appropriate
parameter stores.
