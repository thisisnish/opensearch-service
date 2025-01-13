import json
import logging
from time import sleep

from search.OSearch.OS import os_connect

# from django.conf import settings


logger = logging.getLogger("opensearch")


class OSBulkLoader:
    buffer = ""
    buffer_size = 0
    doc_count = 0
    filtered_indices = []

    def __init__(self, max_size_bytes: int):
        if max_size_bytes:
            # keep old settings code
            # self.max_size = 1024 * int(settings.DATABASES["opensearch"]["buffer_size"])
            self.max_size = 1024 * 1024

    def append_doc(self, index: str, id, document: dict):
        if len(self.filtered_indices) == 0 or index in self.filtered_indices:
            doc_entry = {"index": {"_index": index, "_id": id}}
            self.buffer += json.dumps(doc_entry) + "\n"
            self.buffer += json.dumps(document, default=str).replace("\n", "") + "\n"

            self.buffer_size = len(self.buffer)
            self.doc_count = self.doc_count + 1
            if self.buffer_size > self.max_size:
                self.flush_buffer()

    def flush_buffer(self):
        if self.doc_count > 0:
            logger.debug(
                f"Flushing buffer of {self.doc_count} documents ({self.buffer_size} bytes)"  # noqa
            )
            logger.debug(os_connect().bulk(self.buffer))

            self.reset_buffer()
            sleep(0.1)

    def reset_buffer(self):
        self.buffer = ""
        self.buffer_size = 0
        self.doc_count = 0
