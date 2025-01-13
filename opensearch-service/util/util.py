import uuid


def is_hex_string(s) -> bool:
    return all(c in "0123456789abcdefABCDEF" for c in s)


def generate_hex_string(length: int) -> str:
    return str(uuid.uuid4().hex[:length])


def generate_traceparent_header(trace_id=None, parent_id=None) -> str:
    if not trace_id:
        trace_id = generate_hex_string(32)
    if not parent_id:
        parent_id = generate_hex_string(16)
    return f"00-{trace_id}-{parent_id}-01"


# https://www.w3.org/TR/trace-context/#versioning-of-traceparent
def extract_trace_id_from_traceparent(traceparent=None):
    if not traceparent:
        return None
    trace_split = traceparent.split("-")
    # When the version prefix cannot be parsed (it's not 2 hex characters followed by a dash (-)), the implementation should restart the trace.
    if len(trace_split[0]) != 2 or not is_hex_string(trace_split[0]):
        return None
    # If the size of the header is shorter than 55 characters, the vendor should not parse the header and should restart the trace.
    if len(traceparent) < 55:
        return None
    # Parse trace-id (from the first dash through the next 32 characters). Vendors MUST check that the 32 characters are hex, and that they are followed by a dash (-)
    if len(trace_split[1]) == 32 and is_hex_string(trace_split[1]):
        return trace_split[1]
    return None
