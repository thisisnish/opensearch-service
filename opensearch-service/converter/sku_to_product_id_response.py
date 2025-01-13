def os_sku_to_product_id(response):
    if response is None or not bool(response):
        return response
    product_id_list = []
    if "hits" in response:
        if "hits" in response.get("hits"):
            for hit in response.get("hits").get("hits"):
                if "_source" in hit and "vtexProductId" in hit.get("_source"):
                    product_id_list.append(hit.get("_source").get("vtexProductId"))
    print(f"os_sku_to_product_id: {product_id_list=}")
    return list(set(product_id_list))
