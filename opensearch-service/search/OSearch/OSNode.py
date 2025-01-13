import logging

from search.OSearch.OS import os_connect

logger = logging.getLogger("opensearch")


def get_nodes():
    return os_connect().nodes.info()["nodes"]


def get_node_count() -> int:
    try:
        return len(get_nodes().keys())
    except:  # noqa
        return 1


def get_data_node_count() -> int:
    return_count: int = 0
    all_nodes = {}
    try:
        all_nodes = get_nodes()
    except:  # noqa
        logger.debug("Failed to connect to 'get_nodes' from Opensearch.")

    for node_key in all_nodes.keys():
        for role_name in all_nodes[node_key]["roles"]:
            if role_name == "data":
                return_count = return_count + 1

    return return_count
