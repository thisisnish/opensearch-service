import sys
import uuid

import bcrypt


def print_new_salt(token: str):
    bearer_token_bytes = token.encode("utf-8")
    token_salt_bytes = bcrypt.hashpw(bearer_token_bytes, bcrypt.gensalt())
    token_salt = token_salt_bytes.decode("utf-8")
    if not bcrypt.checkpw(bearer_token_bytes, token_salt_bytes):
        print(f"Salt generation failed for {token}")
    print(f"{token} => {token_salt}")


print("Token generator for Marketplace Search Service")
if len(sys.argv) >= 2:
    print("Found at least one CLI parameter.  Generating salt for each parameter.")
    for arg in sys.argv[1:]:
        print_new_salt(arg)
else:
    print("No CLI parameters found.  Generating new bearer token and salt.")
    bearer_token = str(uuid.uuid4())
    print_new_salt(bearer_token)
