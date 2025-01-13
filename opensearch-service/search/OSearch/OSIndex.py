import json
import logging
import os

from search.OSearch.OS import os_connect
from search.OSearch.OSNode import get_data_node_count

logger = logging.getLogger("opensearch")

OS_SHARDS = os.environ.get("OS_SHARDS", "1")
OS_REPLICAS = os.environ.get(
    "OS_REPLICAS",
    str(
        max(
            0,
            get_data_node_count() - 1,
        )
    ),
)


class OSIndex:
    def exists(index_name: str):
        return os_connect().indices.exists(index_name)

    def list_all(self):
        return os_connect().indices.get("*")

    def delete(index_name: str):
        logger.debug(f"deleting index: {index_name}")
        try:
            os_connect().indices.delete(index=index_name)
        except Exception:
            pass

    def create(index_name: str):
        logger.debug(f"Creating index: {index_name}")

        filename = (
            index_name.split("-")[0] if index_name.__contains__("-") else index_name
        )
        with open(f"./search/indices/{filename}.json", "r") as index_mappings_file:
            index_definition = json.loads(index_mappings_file.read())

            if "settings" not in index_definition:
                index_definition["settings"] = {}
            if "index" not in index_definition["settings"]:
                index_definition["settings"]["index"] = {}

            index_definition["settings"]["index"][
                "number_of_shards"
            ] = OS_SHARDS  # noqa
            index_definition["settings"]["index"][
                "number_of_replicas"
            ] = OS_REPLICAS  # noqa

            os_connect().indices.create(index_name, index_definition)

    def recreate(index_name: str):
        OSIndex.delete(index_name)
        OSIndex.create(index_name)
