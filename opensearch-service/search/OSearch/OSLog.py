import base64
import uuid
from calendar import timegm
from datetime import datetime, timedelta, timezone

from django.conf import settings

from search.OSearch.OSBulkLoader import OSBulkLoader
from search.OSearch.OSIndex import OSIndex


def generate_id(uid: str = None) -> str:
    if uid is None:
        uid = uuid.uuid4()
        code = base64.urlsafe_b64encode(uid.bytes_le)
    else:
        code = base64.urlsafe_b64encode(uuid.UUID(uid).bytes_le)

    cleaned_code = code.decode("utf-8").rstrip("=")
    return cleaned_code


class OSLogger:
    def __init__(self):
        self.bulkloader = OSBulkLoader(10000)
        self.last_flushed = datetime(2000, 1, 1)

    def log_query(self, payload: dict):
        log_dt = datetime.now(timezone.utc)
        log_id = generate_id() + "_" + str(timegm(log_dt.timetuple()))
        log_entry = {
            "log_dt": log_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "log_id": log_id,
            "query": payload,
        }
        self.bulkloader.append_doc(
            "log_query",
            log_id,
            log_entry,
        )
        if (datetime.now() - self.last_flushed) > timedelta(minutes=1):
            self.bulkloader.flush_buffer()
            self.last_flushed = datetime.now()


def create_oslogger():
    if not OSIndex.exists("log_query"):
        OSIndex.create("log_query")
    return OSLogger()


def os_logger():
    if not isinstance(settings.OS_LOGGER, OSLogger):
        settings.OS_LOGGER = create_oslogger()

    return settings.OS_LOGGER
