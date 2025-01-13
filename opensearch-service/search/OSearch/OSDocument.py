import logging

from search.OSearch.OS import os_connect

logger = logging.getLogger("opensearch")


def delete(index_name: str, document_id: str):
    try:
        os_connect().delete(index=index_name, id=document_id)
    except:  # noqa
        logger.debug(f"Error deleting document: {index_name} / {document_id}")
