from typing import Any, Dict, List

from fastapi import HTTPException

from constants.facets import FACET_METADATA, FacetType
from constants.logging import MESSAGE_INTERNAL_SERVICE_ERROR, REQUEST_TYPE_FACETS
from util.logging import get_logger, log_record_for_os_response_error

log = get_logger("app")


def os_to_vtex_facets_response(request, multi_response) -> Dict[str, Any]:
    # print(json.dumps(response, indent=2))
    if multi_response is None or not bool(multi_response):
        return multi_response
    facets = []
    for response in multi_response.get("responses", []):
        if response.get("error"):
            log.error(
                log_record_for_os_response_error(
                    response.get("error", {}), REQUEST_TYPE_FACETS
                )
            )
            raise HTTPException(status_code=500, detail=MESSAGE_INTERNAL_SERVICE_ERROR)
        if response.get("aggregations"):
            aggs = response.get("aggregations")

            # TODO: Add more facets in ECMP-2686

            for facet_enum, facet_data in FACET_METADATA.items():
                match facet_data.facet_type:
                    case FacetType.TEXT:
                        if (
                            facet_data.aggs_name_facet_value() in aggs
                            and facet_data.aggs_name_facet_count() in aggs
                        ):
                            facets.append(
                                build_text_facets(
                                    aggs.get(facet_data.aggs_name_facet_value()),
                                    aggs.get(facet_data.aggs_name_facet_count()),
                                    facet_data.name,
                                    facet_data.key(),
                                )
                            )
                    case FacetType.PRICERANGE:
                        if (
                            facet_data.aggs_name_facet_min() in aggs
                            and "value" in aggs[facet_data.aggs_name_facet_min()]
                            and facet_data.aggs_name_facet_max() in aggs
                            and "value" in aggs[facet_data.aggs_name_facet_max()]
                        ):
                            facets.append(
                                build_price_facet(
                                    aggs[facet_data.aggs_name_facet_min()]["value"],
                                    aggs[facet_data.aggs_name_facet_max()]["value"],
                                )
                            )

    facets = [facet for facet in facets if facet.get("quantity") > 0]
    selected_facets = []
    if request.get("trade_policy", None) is not None:
        selected_facets.append(
            {"key": "trade-policy", "value": request.get("trade_policy", None)}
        )
    if len(request.get("query", "")) > 0:
        selected_facets.append({"key": "ft", "value": request.get("query")})

    response = {
        "facets": facets,
        "sampling": False,
        "breadcrumb": [],
        # Example breadcrumb
        #    {"name": "kettle", "href": "/kettle?map=ft"},
        #    {"name": "Living Fit", "href": "/kettle/living-fit?map=ft,brand"},
        "queryArgs": {
            "query": request.get("query", ""),
            "selectedFacets": selected_facets,
        },
        "translated": False,
    }
    return response


def build_price_facet(min_price: float, max_price: float):
    """
    Generate a simple Price facet to power a slider on FastStore
    Because FastStore only displays 1
    """
    return {
        "values": [
            {
                "quantity": 1,  # hardcode to 1 product because UI doesn't display count
                "name": "",
                "key": "price",
                "selected": False,
                "range": {"from": min_price, "to": max_price},
            }
        ],
        "type": "PRICERANGE",
        "name": "Price",
        "hidden": False,
        "key": "price",
        "quantity": 1,
    }


def build_text_facets(facet_agg, count_aggs, name: str, key: str):
    """
    Build a response Facets dict based on an aggregation result for TEXT type facets
    """
    facet = {
        "values": [],
        "type": "TEXT",
        "name": name,
        "hidden": False,
        "key": key,
        "quantity": count_aggs.get("value", 0),
    }
    if "buckets" in facet_agg:
        # Each bucket represents a different facet value (brand name amongst Brands)
        for bucket in facet_agg["buckets"]:
            # Human-friendly value, the key of the bucket
            facet_value_key = bucket["key"]
            facet_value_key_slug = ""

            # In the sub-aggregation result, get the sluggified-version of the value
            if (
                "slug" in bucket
                and "buckets" in bucket["slug"]
                and len(bucket["slug"]["buckets"]) > 0
                and "key" in bucket["slug"]["buckets"][0]
            ):
                facet_value_key_slug = bucket["slug"]["buckets"][0]["key"]

            # Construct the expected response object for each value of the facet
            facet["values"].append(
                {
                    "id": "",
                    "quantity": bucket["product_count"]["value"],
                    "name": facet_value_key,
                    "key": key,
                    "value": facet_value_key_slug,
                    "selected": False,
                    # TODO: Add selected facets to this href
                    "href": f"{facet_value_key_slug}?map={key}",
                }
            )
    return facet

    # {
    #     "values": [
    #         {
    #             "id": "",
    #             "quantity": 6,
    #             "name": "Battle Ropes",
    #             "key": "product-type",
    #             "value": "battle-ropes",
    #             "selected": false,
    #             "href": "kettle/living-fit/battle-ropes?map=ft,brand,category",
    #         }
    #     ],
    #     "type": "TEXT",
    #     "name": "Category",
    #     "hidden": false,
    #     "key": "product-type",
    #     "quantity": 1,
    # }
