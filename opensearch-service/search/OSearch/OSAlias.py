import logging

from search.OSearch.OS import os_connect
from search.OSearch.OSIndex import OSIndex

logger = logging.getLogger("opensearch")


def alias_exists(alias: str):
    return os_connect().indices.exists_alias(name=alias)


def get_all():
    result = {}
    for ix in os_connect().indices.get("*"):
        aliases = get_by_index(ix)
        if len(aliases) > 0:
            for alias in aliases:
                if alias not in result:
                    result[alias] = []
                result[alias].append(ix)

    return result


def get_by_index(index: str):
    os = os_connect()
    aliases = os.indices.get(index=index)[index]["aliases"]
    return aliases


def get_indices_by_alias(alias: str):
    aliases = get_all()
    if alias in aliases:
        return aliases[alias]
    else:
        return []


def create_alias(alias: str, index: str):
    os = os_connect()
    if os.indices.exists(index=alias):
        OSIndex.delete(alias)

    os.indices.put_alias(index=index, name=alias)


def delete_alias(alias: str, index: str):
    os_connect().indices.delete_alias(index, alias)


def transfer_alias(alias: str, from_index: list, to_index: list):
    os = os_connect()

    if os.indices.exists(index=alias):
        OSIndex.delete(alias)

    actions = {"actions": []}
    for fro in from_index:
        actions["actions"].append({"remove": {"index": fro, "alias": alias}})
    for to in to_index:
        actions["actions"].append({"add": {"index": to, "alias": alias}})

    if os.indices.exists_alias(alias):
        os.indices.update_aliases(body=actions)
    else:
        for to in to_index:
            create_alias(alias, to)


def transfer_all(from_index: str, to_index: str):
    os = os_connect()
    actions = {"actions": []}
    for alias in get_by_index(from_index):
        actions["actions"].append({"remove": {"index": from_index, "alias": alias}})
        actions["actions"].append({"add": {"index": to_index, "alias": alias}})

    os.indices.update_aliases(body=actions)
