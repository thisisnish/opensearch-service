import re

from fastapi import HTTPException, Request

from util.logging import get_logger
from util.util import generate_traceparent_header

REQUIRED_PARAM_PATH_REGEX = r"/trade-policy\/\d+"

log = get_logger("middleware")

ALLOWED_NO_PARAMS_PATH = ["/ping", "/docs"]


async def check_for_required_path_params(request: Request) -> bool:
    full_path = request.url.path
    if full_path in ALLOWED_NO_PARAMS_PATH:
        return True
    if re.search(REQUIRED_PARAM_PATH_REGEX, full_path) is None:
        raise HTTPException(status_code=404, detail="required path params is missing")
    return True


async def extract_traceparent_header(request: Request) -> str:
    traceparent = request.headers.get("traceparent")
    if traceparent and traceparent != "":
        return traceparent

    log.info(
        "Missing traceparent in incoming request header. Generating random hex traceparent."
    )
    return generate_traceparent_header()
