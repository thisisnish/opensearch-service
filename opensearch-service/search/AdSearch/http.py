import json
from typing import Dict

import requests
from structlog.contextvars import bind_contextvars

from search.AdSearch.error import AdSearchError
from util.envvar import is_prod, is_qa
from util.logging import get_logger
from util.session import TimePersistedSession
from util.util import generate_hex_string, generate_traceparent_header

logger = get_logger(__name__)
session = TimePersistedSession()


def get_base_url() -> str:
    if is_prod():
        return "https://retailmedia.prod.ecmsrvcs.com"
    if is_qa():
        return "https://retailmedia.qa.ecmsrvcs.com"
    return "https://retailmedia.dev.ecmsrvcs.com"


def check_metadata_exists(meta: any) -> bool:
    """
    Returns TRUE iff meta consists of any valid information
    Args:
        meta: json object
    """
    if isinstance(meta, dict):
        return all(check_metadata_exists(v) for v in meta.values())
    elif isinstance(meta, list):
        return all(check_metadata_exists(item) for item in meta)
    elif meta is None or meta == "":
        return False
    else:
        # If it's any other data type, consider it non-empty
        return True


class AdHttpService:
    def __init__(self):
        self.base_url = get_base_url()

    def get_ads(
        self, trace_id: str, headers: Dict[str, str], params: Dict[str, str]
    ) -> dict:
        """
        Sends a GET request to the AdSearch API

        Args:
            trace_id (str): The trace id of incoming request
            headers (Dict[str, str]): Dictionary of HTTP Headers to send with the Request
            params (Dict[str, str]): Dictionary of Parameters to send with the Request

        Returns:
            dict: JSON response from the AdSearch API
        """
        try:
            params["info"] = "y"
            parent_id = generate_hex_string(16)
            bind_contextvars(parent_id=parent_id)
            # https://www.w3.org/TR/trace-context/#relationship-between-the-headers
            traceparent_value = generate_traceparent_header(trace_id, parent_id)
            headers["traceparent"] = traceparent_value
            response = session.get(
                f"{self.base_url}/sponsored",
                params=params,
                headers=headers,
                timeout=2,
            )
            response.raise_for_status()
            ads_success_log = {
                "status": response.status_code,
            }
            logger.info(ads_success_log)
            return response.json()
        except requests.exceptions.Timeout as e:
            # when timeout happens, log error but continue operation
            logger.error(f"RMN request timeout: {e}")
            return {}
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            status_code = http_err.response.status_code
            message = http_err.response.text
            raise AdSearchError(message, status_code, http_err.response)
        except json.decoder.JSONDecodeError as json_err:
            logger.error(f"JSON decoding error occurred: {json_err}")
            status_code = 400
            message = json_err.msg
            raise AdSearchError(message, status_code, json_err.msg)
