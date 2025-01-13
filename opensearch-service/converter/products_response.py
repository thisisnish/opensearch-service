from typing import Any, Dict, List


# https://github.com/vtex/faststore/blob/c2b332f305a3066145d5ca61cd1bbb47c95420ea/packages/api/src/platforms/vtex/clients/search/types/ProductSearchResult.ts#L1
def os_to_vtex_products_response(request, response) -> Dict[str, Any]:
    if response is None or not bool(response):
        return response
    results = list(map(lambda _hit: _hit["_source"], response["hits"]["hits"]))
    return {
        # "metadata": {"count": len(results), "hits": response["hits"]["total"]["value"]},
        "recordsFiltered": response["aggregations"]["result_count"]["value"],
        "pagination": os_to_vtex_pagination(request, response),
        "options": None,
        "products": build_products(response["hits"]["hits"]),
        "sampling": False,
        "translated": False,
        # consider how to pass in request parameters
        "locale": "en-US",
        "query": request["query"],
        "operator": "and",  # or "or" ?
        "fuzzy": request.get("fuzzy", "0"),
    }


def build_products(hits) -> List:
    results = []
    for hit in hits:
        product = dict()
        product.update(hit["_source"]["productResult"])

        # initialize skuSpecifications if it doesn't currently exist
        if product.get("skuSpecifications") is None:
            product["skuSpecifications"] = []

        items = []
        for inner_hit in hit["inner_hits"]["skus"]["hits"]["hits"]:
            item = dict()
            item.update(inner_hit["_source"]["productSkuResult"]["item"])
            item.update(inner_hit["_source"]["offerItemResult"])

            #########################
            # Aggregate Sku specifications

            inner_sku_spec = (
                inner_hit.get("_source")
                .get("productSkuResult", {})
                .get("skuSpecifications", [])
            )

            for spec in inner_sku_spec if inner_sku_spec is not None else []:
                field_name = spec.get("field").get("name")

                # Find the matching skuSpec object to add the sku's value
                prod_sku_spec_match = [
                    prod_sku_spec
                    for prod_sku_spec in product.get("skuSpecifications")
                    if field_name == prod_sku_spec.get("field").get("name")
                ]

                if len(prod_sku_spec_match) == 0:
                    product.get("skuSpecifications").append(
                        {
                            "field": {"name": field_name, "originalName": field_name},
                            "values": spec.get("values"),
                        }
                    )
                else:
                    # for each productResult.skuSpecification matching the field.name
                    for prod_sku_spec in prod_sku_spec_match:
                        # for each value
                        for spec_value in spec.get("values", []):
                            if spec_value not in prod_sku_spec.get("values", []):
                                prod_sku_spec.setdefault("values", []).append(
                                    spec_value
                                )

            # End aggregate sku specifications
            #########################
            items.append(item)

        product["items"] = items
        results.append(product)

    return results


def os_to_vtex_pagination(request, response):
    return {
        "count": len(response["hits"]["hits"]),
        "current": {"index": request["page"]},
        "before": [],
        "after": [],
        "perPage": request["count"],
        "next": {"index": request["page"] + 1},  # None if at end
        "previous": {"index": request["page"] - 1} if request["page"] > 1 else {},
        "first": {"index": 1},
        "last": None,
    }
