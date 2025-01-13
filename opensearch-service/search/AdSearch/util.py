def inject_ads(organic_products: list, ad_products: list) -> list:
    organic_count = len(organic_products)
    for ad_product in ad_products:
        ad_position = (
            ad_product["adMetaBackend"]["position"]
            if "adMetaBackend" in ad_product
            and "position" in ad_product["adMetaBackend"]
            else -1
        )
        if_more_than = (
            ad_product["adMetaBackend"]["ifMoreThan"]
            if "adMetaBackend" in ad_product
            and "ifMoreThan" in ad_product["adMetaBackend"]
            else organic_count
        )
        if if_more_than > organic_count or ad_position == -1:
            continue
        if "skuInfo" in ad_product:
            new_ad_product = dict()
            if "productResult" in ad_product["skuInfo"]:
                new_ad_product.update(ad_product["skuInfo"]["productResult"])
            item = {}
            if "productSkuResult" in ad_product["skuInfo"]:
                item = ad_product["skuInfo"]["productSkuResult"]["item"]
            if not item.get("sellers") and "offerItemResult" in ad_product["skuInfo"]:
                item.update(ad_product["skuInfo"]["offerItemResult"])
            new_ad_product["items"] = [item]
            new_ad_product["adMetaUi"] = ad_product.get("adMetaUi")
            organic_products.insert(ad_position, new_ad_product)
    return organic_products
