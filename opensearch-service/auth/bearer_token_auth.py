import os

import bcrypt
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from util.envvar import BEARER_TOKEN_LIST_ENV_VALUE
from util.logging import get_logger
from util.time import current_milli_time

BEARER_TOKEN_LIST_ENV_KEY = "SALTED_BEARER_TOKEN_LIST"

log = get_logger("app")


class TokenBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(TokenBearer, self).__init__(auto_error=auto_error)
        if not BEARER_TOKEN_LIST_ENV_VALUE:
            raise Exception(f"No environment variable for {BEARER_TOKEN_LIST_ENV_KEY}")
        # Convert each salted bearer token from a str to bytes
        self._valid_bearer_hash_list = [
            bearer_token.encode("utf-8")
            for bearer_token in os.environ.get(BEARER_TOKEN_LIST_ENV_KEY, "").split(",")
        ]

    async def __call__(self, request: Request):
        start = current_milli_time()
        credentials: HTTPAuthorizationCredentials | None = await super(
            TokenBearer, self
        ).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=403, detail="Invalid authentication scheme."
                )
            if not self.verify_bearer_token(credentials.credentials):
                raise HTTPException(
                    status_code=403, detail="Invalid token or expired token."
                )
            end = current_milli_time()
            log.info({"verify_latency": end - start})
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

    # Compare hashes of input bearer_token against hashes of valid bearer tokens
    def verify_bearer_token(self, bearer_token: str) -> bool:
        bearer_token_bytes = bearer_token.encode("utf-8")
        return any(
            bcrypt.checkpw(bearer_token_bytes, bearer_hash)
            for bearer_hash in self._valid_bearer_hash_list
        )
