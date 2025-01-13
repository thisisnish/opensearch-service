import os

import boto3
from django.conf import settings
from opensearchpy import OpenSearch, RequestsAWSV4SignerAuth, RequestsHttpConnection

# Hack to make settings work, clean up later  please reset
settings.configure()
settings.RELEVANCE_THRESHOLD = "70"
settings.OS_CONNECTION = None


def create_connection():
    if settings.DATABASES.get("opensearch") is not None:
        host = settings.DATABASES["opensearch"]["host"]
        port = settings.DATABASES["opensearch"]["port"]
        username = settings.DATABASES["opensearch"]["user"]
        password = settings.DATABASES["opensearch"]["password"]
        timeout = settings.DATABASES["opensearch"]["timeout"]
        insecure = settings.DATABASES["opensearch"]["insecure"]

        if settings.DEBUG or insecure:
            return OpenSearch(
                hosts=[{"host": host, "port": port}],
                http_compress=True,
                http_auth=(username, password),
                timeout=int(timeout),
            )

        return OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_compress=True,
            http_auth=(username, password),
            use_ssl=True,
            timeout=int(timeout),
        )
    else:
        # cluster endpoint, for example: my-test-domain.us-east-1.es.amazonaws.com
        host = os.environ["OPEN_SEARCH_HOST"]
        region = "us-east-2"
        service = "es"
        # TODO: Parameterize session info
        credentials = None
        auth = None
        if "OS_TEMP_PASSWORD" in os.environ:
            # local dev-box testing on non-standard index
            auth = ("mu", os.environ["OS_TEMP_PASSWORD"])
            print("OS Auth with username/password")
        elif "AWS_PROFILE" in os.environ:
            # If a profile is specified, use it
            profile_name = os.environ["AWS_PROFILE"]
            credentials = boto3.Session(profile_name).get_credentials()
            auth = RequestsAWSV4SignerAuth(credentials, region, service)
            print(f"OS Auth with AWS Profile {profile_name}")
        else:
            # Otherwise use default session, the
            credentials = boto3.Session().get_credentials()
            auth = RequestsAWSV4SignerAuth(credentials, region, service)
            print("OS Auth with Default AWS Session")

        os_client = OpenSearch(
            hosts=[{"host": host, "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            pool_maxsize=20,
        )
        return os_client


def os_connect():
    if not isinstance(settings.OS_CONNECTION, OpenSearch):
        settings.OS_CONNECTION = create_connection()

    return settings.OS_CONNECTION
