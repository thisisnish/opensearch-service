import json
import uuid

import requests
from fastapi import Request

from constants.logging import REQUEST_TYPE_PRODUCT_DETAIL
from util.envvar import PULSE_API_KEY, STAGE, is_prod
from util.logging import get_logger
from util.storefront import storefront_domain_for_trade_policy
from util.time import current_milli_time

log = get_logger("app")


def _pulse_headers():
    headers = {"Content-Type": "application/json"}
    if PULSE_API_KEY:
        headers["x-api-key"] = PULSE_API_KEY
    return headers


def _pulse_url():
    if is_prod():
        return (
            "https://aw8xjb50m9.execute-api.us-east-2.amazonaws.com/Prod/sendtokinesis"
        )
    else:
        return (
            "https://ul8i8hni4k.execute-api.us-east-2.amazonaws.com/Dev/sendtokinesis"
        )


PULSE_DEFAULT_HEADERS = _pulse_headers()


def pulse_pdp_quantities(response, query_string, trade_policy, req: Request):
    if is_prod() and not PULSE_API_KEY:
        # API Key not required for non-prod stages
        log.error(
            {
                "stage": STAGE,
                "request_type": REQUEST_TYPE_PRODUCT_DETAIL,
                "event": "NO_PULSE_API_KEY",
            }
        )
        return
    start = current_milli_time()
    items = []
    for product in response.get("products", []):
        product_id = product.get("productId", "0")
        product_id_int = int(product_id)
        for item in product.get("items", []):
            found_quantity = False
            sku_id = item.get("itemId", "0")
            sku_id_int = int(sku_id)
            for seller in item.get("sellers", []):
                quantity = seller.get("commertialOffer", {}).get(
                    "AvailableQuantity", -1
                )
                seller_id = seller.get("sellerId", "1")
                if quantity >= 0 and seller_id != "1":
                    found_quantity = True
                    items.append(
                        {
                            "item_id": product_id_int,
                            "item_variant": sku_id_int,
                            "quantity": quantity,
                        }
                    )
            if not found_quantity:
                items.append(
                    {
                        "item_id": product_id_int,
                        "item_variant": sku_id_int,
                        "quantity": 0,
                    }
                )

    meta_data = dict()
    if req.headers.get("x-user-agent"):
        meta_data["user_agent"] = req.headers.get("x-user-agent")
    if req.headers.get("x-cart-id"):
        meta_data["cart_id"] = req.headers.get("x-cart-id")
    if req.headers.get("x-referer"):
        meta_data["referer"] = req.headers.get("x-referer")

    # Schema documentation from the Data team.  See page 6.
    # https://hearstpm.sharepoint.com/:w:/r/sites/HearstECommerce/_layouts/15/Doc.aspx?sourcedoc=%7B79E27C76-F1E8-4A2E-B494-E4B36D169135%7D&file=Checkout%20events%20for%20Pulse%20Clickstream.docx&action=default&mobileredirect=true
    payload = {
        "data": {
            "event_id": str(uuid.uuid4()),
            # consider changing below line to parsing from a header if it exists
            "site_group_name": storefront_domain_for_trade_policy(trade_policy),
            "site_name": f"shop.{storefront_domain_for_trade_policy(trade_policy)}",
            "event_timestamp": current_milli_time(),
            "event": {
                "name": "marketplace-search-service-pdp",
                "params": {
                    "search_term": query_string,
                    "items": items,
                },
            },
            "meta_data": meta_data,
        }
    }

    seq_number = ""
    status_code = 0
    try:
        response = requests.post(
            _pulse_url(), data=json.dumps(payload), headers=PULSE_DEFAULT_HEADERS
        )
        status_code = response.status_code
        if response.status_code == 200:
            seq_number = json.loads(response.content).get("SequenceNumber", "")
    except requests.RequestException as e:
        log.error(
            {
                "stage": STAGE,
                "request_type": REQUEST_TYPE_PRODUCT_DETAIL,
                "route": req.url.path + "?" + req.url.query,
                "error": e,
            }
        )
    # Uncomment print as needed for local testing
    # print(json.dumps(payload, indent=2))
    log.info(
        {
            "stage": STAGE,
            "pulse_latency": current_milli_time() - start,
            "request_type": REQUEST_TYPE_PRODUCT_DETAIL,
            "route": req.url.path + "?" + req.url.query,
            "pulse_sequence_number": seq_number,
            "pulse_status_code": status_code,
        }
    )
