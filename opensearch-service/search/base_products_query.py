import json

from constants.facets import FacetEnum
from search.OSearch.OSQuery import QueryBuilder

TEXT_QUERY_MIN_SCORE = 0.5


# Base class to handle common query inputs for products
# Extendable for ProductSearch and Facets that have different response schemas
class BaseProductQuery:
    def __init__(self, index_name: str):
        self._os_query: QueryBuilder = QueryBuilder(index_name)
        self._index: str = index_name
        self._text_query_list: list[str] = []
        self._size = 10
        self._page = 1
        self._trade_policy = None
        self._brand_list: list[str] = []
        self._category_tier_name_list: dict[str, list[str]] = dict()
        self._product_cluster_id_list: list[str] = []
        self._product_type_list: list[str] = []
        self._sku_id_list: list[str] = []
        self._product_id_list: list[str] = []
        self._link_text_list: list[str] = []
        self._return_includes_list: list[str] = []
        self._return_excludes_list: list[str] = []
        self._collapse_source_list: list[str] = []
        self._min_price_range = None
        self._max_price_range = None
        self._sort_mode = ""
        self._exclude_out_of_stock = False
        self._markdown_only: bool = False
        self._seller_id_list: list[str] = []

        return

    def has_trade_policy(self):
        return not (self._trade_policy is None)

    def brand(self, brand_name):
        self._brand_list.append(brand_name)

    def category(self, category_tier, category_name):
        if category_tier not in self._category_tier_name_list:
            self._category_tier_name_list[category_tier] = []
        self._category_tier_name_list[category_tier].append(category_name)

    def product_cluster_id(self, product_cluster_id):
        self._product_cluster_id_list.append(product_cluster_id)

    def product_type(self, product_type):
        self._product_type_list.append(product_type)

    def page_size(self, size):
        self._size = size
        return self

    def page_number(self, page):
        self._page = page
        return self

    def trade_policy(self, tp):
        self._trade_policy = tp
        return self

    def get_trade_policy(self):
        return self._trade_policy

    def text_query(self, text):
        if text and len(text) > 0:
            self._text_query_list.append(text)
        return self

    def collapse_skus(self, collapse_source: list[str]):
        self._collapse_source_list += collapse_source
        return self

    def sku_ids(self, sku_id_list: list[str]):
        self._sku_id_list += sku_id_list
        return self

    def product_ids(self, product_id_list: list[str]):
        self._product_id_list += product_id_list
        return self

    def link_text(self, link_text_list):
        self._link_text_list += link_text_list
        return self

    def price_range(self, min_price_range, max_price_range):
        self._min_price_range = min_price_range
        self._max_price_range = max_price_range
        return self

    def return_fields(self, includes: list[str] = [], excludes: list[str] = []):
        self._return_includes_list += includes
        self._return_excludes_list += excludes
        return self

    def sort(self, sort: str):
        self._sort_mode = sort
        return self

    def exclude_out_of_stock(self):
        self._exclude_out_of_stock = True
        return self

    def include_markdown_only(self):
        self._markdown_only = True
        return self

    def sellers(self, seller_id: str):
        self._seller_id_list.append(seller_id)
        return self

    def build(self):
        self._os_query.return_fields(
            includes=self._return_includes_list, excludes=self._return_excludes_list
        )

        if len(self._collapse_source_list) > 0:
            self._os_query.collapse(
                "vtexProductId",
                {
                    "name": "skus",
                    "size": 500,
                    "_source": self._collapse_source_list,
                },
            )

        for text in self._text_query_list:
            self._os_query.should(
                {
                    "multi_match": {
                        "query": text,
                        # any analyzer listed here must exist on the index, else the query will fail
                        "analyzer": "global_product_synonyms",
                        "fields": [
                            "productResult.productName^3",
                            "productResult.brand^3",
                            "productResult.description",
                        ],
                    }
                }
            )
            self._os_query.query["min_score"] = TEXT_QUERY_MIN_SCORE

        if len(self._sku_id_list) > 0:
            self._os_query.filter({"terms": {"vtexSkuId": self._sku_id_list}})

        if len(self._product_id_list) > 0:
            self._os_query.filter({"terms": {"vtexProductId": self._product_id_list}})

        if len(self._link_text_list) > 0:
            self._os_query.filter(
                {"terms": {"productResult.linkText.keyword": self._link_text_list}}
            )

        if len(self._brand_list) > 0:
            self._os_query.filter(
                {"terms": {"searchProductFields.brand-slug.keyword": self._brand_list}}
            )

        for tier, names in self._category_tier_name_list.items():
            self._os_query.filter(
                {"terms": {f"searchTaxonomy.{tier}-slug.keyword": names}}
            )

        if len(self._product_type_list) > 0:
            self._os_query.filter(
                {
                    "terms": {
                        "searchProductFields.product-type-slug.keyword": self._product_type_list
                    }
                }
            )

        if len(self._product_cluster_id_list) > 0:
            self._os_query.filter(
                {
                    "terms": {
                        "productResult.productClusters.id": self._product_cluster_id_list
                    }
                }
            )

        self._os_query.filter(QueryBuilder.equals("tradePolicy", self._trade_policy))

        if self._max_price_range is not None:
            self._os_query.filter(
                {
                    "range": {
                        "searchSellers.commertialOffer.Price": {
                            "gte": self._min_price_range,
                            "lte": self._max_price_range,
                        }
                    }
                }
            )

        if self._exclude_out_of_stock:
            self._os_query.filter(
                {
                    "range": {
                        "searchSellers.commertialOffer.AvailableQuantity": {"gt": 0}
                    }
                }
            )

        if self._markdown_only:
            self._os_query.filter(
                {"term": {"searchSellers.commertialOffer.isMarkdown": True}}
            )

        if len(self._seller_id_list) > 0:
            self._os_query.filter(
                {"terms": {"searchSellers.sellerId.keyword": self._seller_id_list}}
            )

        self._os_query.paginate(self._size, self._page)

        match self._sort_mode:
            case "price:asc":
                self._os_query.sort("searchSellers.commertialOffer.Price", "asc")
            case "price:desc":
                self._os_query.sort("searchSellers.commertialOffer.Price", "desc")
            case "release:desc":
                self._os_query.sort("productResult.releaseDate", "desc")
        # else, assume relevance score

        # TODO: ECMP-XXXX additional sort fields
        # # discount:desc # future
        # # name:asc # future
        # # name:desc # future
        # # orders:desc # future

        return self

    def execute_search(self):
        # TODO: Refactor to use ABC, maybe?
        raise NotImplementedError("Please implement this method")
