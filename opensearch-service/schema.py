import json
import re

print("test")

# TODOs
# Solve for PriceRange at product level
# Schema for categories, use CC categories as example
# Seller Name (blank) but put in another index to cache in memory for MSS
# Product Clusters and Collections
# Product Properties


def pprint(json_doc):
    print(json.dumps(json_doc, indent=2))


# Sluggify words to match inputs from FS Search
# See https://github.com/vtex/faststore/blob/main/packages/api/src/platforms/vtex/utils/slugify.ts#L41-L47
# For better handling of characters with diacritical marks
def sluggy(input_string):
    # remove commas
    # remove non-alphanumerics (for now)
    return re.sub("[^A-Za-z0-9]+", "-", re.sub("/,/g", "", input_string.lower()))


def build_product_result(d):
    # Build product-specific response objects
    productId = d["vtexProductId"]
    product_result = {
        "productId": d["vtexProductId"],
        "productName": d["productAttributes"]["ProductName"],
        "brand": d["productAttributes"]["BrandName"],
        "brandId": d["productAttributes"]["BrandId"],
        "cacheId": f"sp-{productId}",
        # strip leading "/" and trailing "/p"
        "linkText": d["productAttributes"]["DetailUrl"][1:-2],
        "productReference": d["productAttributes"]["ProductRefId"],
        "categoryId": "??? frontend",
        "clusterHighlights": "??? frontend maybe",
        "productClusters": "??? frontend maybe how to refine",
        "categories": ["??? frontend"],
        "categoriesIds": ["??? frontend"],
        "link": d["productAttributes"]["DetailUrl"],
        "description": d["productAttributes"]["ProductDescription"],
        # items: see product_sku_result and offer_item_result_map[trade_policy]
        # skuSpecifications: see productSkuResult
        "priceRange": "???",
        "specificationGroups": [],  # constructed below
        "properties": ["array of things"],  # combine and simplified sku/product specs
        "selectedProperties": [],  # empty per convo w/ Graham
        "releaseDate": d["productAttributes"]["ReleaseDate"],
    }

    # Build product-level specification groups
    specGroups = {
        "allSpecifications": {
            "originalName": "allSpecifications",
            "name": "allSpecifications",
            "specifications": [],
        }
    }
    for prodSpec in d["productAttributes"]["ProductSpecifications"]:
        field_group_name = prodSpec["FieldGroupName"]
        if field_group_name not in specGroups:
            specGroups[field_group_name] = {
                "originalName": field_group_name,
                "name": field_group_name,
                "specifications": [],
            }
        specGroups[field_group_name]["specifications"].append(  # type: ignore [attr-defined]
            {
                "originalName": prodSpec["FieldName"],
                "name": prodSpec["FieldName"],
                "values": prodSpec["FieldValues"],
            }
        )
        # And do it for the allSpecifications groups
        specGroups["allSpecifications"]["specifications"].append(  # type: ignore [attr-defined]
            {
                "originalName": prodSpec["FieldName"],
                "name": prodSpec["FieldName"],
                "values": prodSpec["FieldValues"],
            }
        )
    for specGroup in specGroups.values():
        product_result["specificationGroups"].append(specGroup)
    return product_result


def build_product_sku_result(d):
    # Build sku-specific response objects
    product_sku_result = {"skuSpecifications": []}
    for skuSpec in d["productAttributes"]["SkuSpecifications"]:
        results_sku_spec = {
            "field": {
                "name": skuSpec["FieldName"],
                "originalName": skuSpec["FieldName"],
            },
            "values": [dict()],
        }
        values = []
        for specValue in skuSpec["FieldValues"]:
            values.append({"name": specValue, "originalName": specValue})
        results_sku_spec["values"] = values
        product_sku_result["skuSpecifications"].append(results_sku_spec)

    # build the Item for the sku
    product_sku_result["item"] = {
        "itemId": d["vtexSkuId"],
        "name": d["productAttributes"]["ProductName"],
        "nameComplete": d["productAttributes"]["NameComplete"],
        "complementName": d["productAttributes"]["ComplementName"],
        "ean": "???",  # keep looking for a better example
        "referenceId": [],  # populated below
        "measurementUnit": d["productAttributes"]["MeasurementUnit"],
        "modalType": d["productAttributes"]["ModalType"],
        "images": [],  # populated below
        "Videos": [],  # capital V what? empty for now, add as feature later
        "variations": [],
        # "sellers": [],  # sourced from offer changes; stored in different element
        "attachments": [],  # later
        "isKit": d["productAttributes"]["IsKit"],  # usually false, but don't default
        "kitItems": [],  # later
    }
    # item.referenceId
    ref_ids = []
    for key in d["productAttributes"]["AlternateIds"]:
        ref_id = dict()
        ref_id["Key"] = key
        ref_id["Value"] = d["productAttributes"]["AlternateIds"][key]
        ref_ids.append(ref_id)
    product_sku_result["item"]["referenceId"] = ref_ids
    # item.images
    images = []
    for imageIn in d["productAttributes"]["Images"]:
        image = dict()
        image["imageId"] = imageIn["FileId"]
        # image["cacheId"] = imageIn["FileId"], in example, not in schema?
        image["imageLabel"] = imageIn["ImageName"]
        image["imageTag"] = ""
        image["imageUrl"] = imageIn["ImageUrl"]
        image["imageText"] = imageIn["ImageName"]
        images.append(image)
    product_sku_result["item"]["images"] = images
    # item.variations
    variations = []
    for skuSpec in d["productAttributes"]["SkuSpecifications"]:
        results_sku_spec = {
            "name": skuSpec["FieldName"],
            "values": skuSpec["FieldValues"],
        }
        variations.append(results_sku_spec)
    product_sku_result["item"]["variations"] = variations
    # flatten skuSpec in item
    for skuSpec in d["productAttributes"]["SkuSpecifications"]:
        values = []
        for specValue in skuSpec["FieldValues"]:
            values.append(specValue)
        product_sku_result["item"][skuSpec["FieldName"]] = values
    return product_sku_result


def build_offer_item_result_map(d, sales_channels):
    print(sales_channels)
    # Pull Seller info from offer Attributes
    offer_item_result_map = dict()
    for x in sales_channels:
        offer_item_result_map[x] = dict({"sellers": []})
    print(offer_item_result_map)
    sellers = []
    for sellerOffer in d["offerAttributes"][0]["sellersOffers"]:
        if sellerOffer["sellerId"] == "1":
            continue
        for salesChannelOffer in sellerOffer["salesChannelOffer"]:
            if salesChannelOffer["salesChannelId"] == "1":  # Main
                continue
            seller = dict()
            # drop seller 1 once I have better sample input
            # IS Response doesn't include split by sales channel/trade policy
            # Store price/inventory from any TP?
            seller["sellerId"] = sellerOffer["sellerId"]
            # no really, WTF, we need to get all Sellers as another index for local cache
            seller["sellerName"] = "WTF?"
            seller["addToCartLink"] = ""  # blank in examples
            seller["sellerDefault"] = False  # true for best offer?
            comm_offer = {
                # real values
                "Price": salesChannelOffer["price"],
                "ListPrice": salesChannelOffer["listPrice"],
                "PriceWithoutDiscount": salesChannelOffer["priceWithoutDiscount"],
                "AvailabilityQuantity": salesChannelOffer["availableQuantity"],
                # default values
                "DeliverySlaSamplesPerRegion": {},
                "DeliverySlaSamples": [],
                "discountHighlights": [],
                "Installments": [],
                "taxPercentage": 0,
                "Tax": 0,
                "GiftSkuIds": [],
                "BuyTogether": [],
                "ItemMetadataAttachment": [],
                "RewardValue": 0,
                "PriceValidUntil": None,
                "GetInfoErrorMessage": None,
                "CacheVersionUsedToCallCheckout": "",
                "teasers": [],
            }
            seller["commertialOffer"] = comm_offer
            offer_item_result_map[salesChannelOffer["salesChannelId"]][
                "sellers"
            ].append(seller)
        # sellers.append(seller)
    #  offer_item_result_map["sellers"] = sellers
    return offer_item_result_map


def build_search_product_fields(d):
    # search parameters
    # sluggify path params
    search_product_fields = dict()
    search_product_fields["brand"] = sluggy(d["productAttributes"]["BrandName"])
    # search-ify sku specs that are filters
    for skuSpec in d["productAttributes"]["SkuSpecifications"]:
        if skuSpec["IsFilter"]:
            values = []
            for specValue in skuSpec["FieldValues"]:
                values.append(sluggy(specValue))
            search_product_fields[skuSpec["FieldName"]] = values
    # don't sluggify query params
    search_product_fields["productName"] = d["productAttributes"]["ProductName"]
    search_product_fields["description"] = d["productAttributes"]["ProductDescription"]
    return search_product_fields


# convert a ProductChangeSnapshot object to the schema to store in OS
def pcs_to_os_documents(d):
    sales_channels_strs = [
        f"{x}" for x in d["productAttributes"]["SalesChannels"] if x != 1
    ]

    product_result = build_product_result(d)
    product_sku_result = build_product_sku_result(d)
    offer_item_result_map = build_offer_item_result_map(d, sales_channels_strs)
    search_product_fields = build_search_product_fields(d)

    docs = []
    for sales_channel in sales_channels_strs:
        doc = {
            "vtexProductId": d["vtexProductId"],
            "vtexSkuId": d["vtexSkuId"],
            "tradePolicy": sales_channel,
            "productResult": product_result,
            "productSkuResult": product_sku_result,
            "offerItemResult": offer_item_result_map[sales_channel],
            "searchProductFields": search_product_fields,
        }
        docs.append(doc)

    return docs


with open("sample/sqs_body-1711068568.json") as file:
    in_doc = json.load(file)
    file.close()
    pprint(in_doc)
    out_doc = pcs_to_os_documents(in_doc)

with open("os_document.json", "w") as os_f:
    os_f.write(json.dumps(out_doc, indent=2))
    os_f.write("\n")  # blank line at end
