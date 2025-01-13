from constants.facets import FACET_METADATA, FacetEnum, FacetType
from search.base_products_query import BaseProductQuery
from search.OSearch.OSQuery import MultiQuery, QueryBuilder
from util.envvar import STAGE
from util.logging import get_logger
from util.time import current_milli_time

log = get_logger("app")


class FacetsSearchQuery(BaseProductQuery):
    def __init__(self, index_name):
        super().__init__(index_name)
        self.return_fields(includes=["vtexProductId"])
        self.collapse_skus(["vtexSkuId"])
        self.exclude_out_of_stock()  # always exclude OOS skus in facets
        return

    def execute_search(self):
        """
        Each facet query must not apply any filter parameters on that facet's attribute to enable multi-select of facets.
        If filter parameters are "brand in [geologie,flybird-fitness]" and "product-type in [dumbbells,skin-care]",
        the facet query for brand must not apply [geologie,flybird-fitness] otherwise only those two options would be
        in the response and no other brands would be selectable.

        Prior to executing a search, this FacetSearchQuery creates N FacetSubQuery objects for a multisearch.
        For each facet, if there are corresponding filter parameters on that attribute, then create a facet query for
        that facet only, dropping the filter parameters for the facet.  Otherwise, add it to the `no_filter_facets` list.

        The facets that have no filter attributes get combined into one query since they'll share the same filters.
        :return: Multi-query response dict with { responses: [] } containing an array of query responses.
        """
        mq = MultiQuery()
        # List of facets that are not filtered by the inputs
        no_filter_facets = []
        for facet_enum, facet_data in FACET_METADATA.items():
            match facet_enum:
                case FacetEnum.BRAND:
                    if len(self._brand_list) > 0:
                        self.build_add_facet_sub_query([facet_enum], mq)
                    else:
                        no_filter_facets.append(facet_enum)
                case FacetEnum.PRICE:
                    if self._max_price_range is not None:
                        self.build_add_facet_sub_query([facet_enum], mq)
                    else:
                        no_filter_facets.append(facet_enum)
                case FacetEnum.PRODUCT_TYPE:
                    if len(self._product_type_list) > 0:
                        self.build_add_facet_sub_query([facet_enum], mq)
                    else:
                        no_filter_facets.append(facet_enum)
        if len(no_filter_facets) > 0:
            self.build_add_facet_sub_query(no_filter_facets, mq)

        os_start = current_milli_time()
        mq_response = mq.execute()
        log.info(
            {
                "stage": STAGE,
                "os_latency": current_milli_time() - os_start,
                "request_type": "facet",
            }
        )
        return mq_response

    def build_add_facet_sub_query(
        self, facet_enum_list: list[FacetEnum], mq: MultiQuery
    ):
        facet_sub_query = _FacetSubQuery(self._index, self, facet_enum_list)
        facet_sub_query.append_to_multi_query(mq)


class _FacetSubQuery(BaseProductQuery):
    def __init__(
        self,
        index_name,
        facet_main_query: FacetsSearchQuery,
        facet_enum_list: list[FacetEnum],
    ):
        super().__init__(index_name)
        self._facet_enum_list = facet_enum_list

        self.return_fields(
            includes=facet_main_query._return_includes_list,
            excludes=facet_main_query._return_excludes_list,
        )

        if FacetEnum.BRAND not in facet_enum_list:
            for brand in facet_main_query._brand_list:
                self.brand(brand)
        if FacetEnum.PRODUCT_TYPE not in facet_enum_list:
            for product_type in facet_main_query._product_type_list:
                self.product_type(product_type)
        if FacetEnum.PRICE not in facet_enum_list:
            if facet_main_query._max_price_range is not None:
                self.price_range(
                    facet_main_query._min_price_range, facet_main_query._max_price_range
                )

        for (
            cat_tier,
            cat_value_list,
        ) in facet_main_query._category_tier_name_list.items():
            for cat_value in cat_value_list:
                self.category(cat_tier, cat_value)
        for product_cluster_id in facet_main_query._product_cluster_id_list:
            self.product_cluster_id(product_cluster_id)
        for text_query in facet_main_query._text_query_list:
            self.text_query(text_query)
        if len(facet_main_query._collapse_source_list) > 0:
            self.collapse_skus(facet_main_query._collapse_source_list)

        self.page_number(facet_main_query._page)
        self.page_size(facet_main_query._size)
        self.trade_policy(facet_main_query._trade_policy)
        self.sku_ids(facet_main_query._sku_id_list)
        self.product_ids(facet_main_query._product_id_list)
        self.link_text(facet_main_query._link_text_list)

        # always exclude out of stock skus in facets
        self.exclude_out_of_stock()

    def append_to_multi_query(self, mq: MultiQuery):
        self.build()
        if type(self._os_query) is QueryBuilder:
            mq.append_query(
                query_builder=self._os_query,
                index=self._index,
                pagination_props={},
                sort_order="",
            )
        else:
            raise AssertionError("self._os_query not instantiated!")

    def build(self):
        super().build()

        if "aggs" not in self._os_query.query:
            self._os_query.query["aggs"] = {}

        for facet_enum in self._facet_enum_list:
            facet_data = FACET_METADATA[facet_enum]
            match facet_data.facet_type:
                case FacetType.TEXT:
                    self._os_query.query["aggs"][
                        facet_data.aggs_name_facet_value()
                    ] = aggs_facet(facet_data.value_location, facet_data.slug_location)
                    self._os_query.query["aggs"][
                        facet_data.aggs_name_facet_count()
                    ] = aggs_facet_count(facet_data.value_location)
                case FacetType.PRICERANGE:
                    self._os_query.query["aggs"][facet_data.aggs_name_facet_min()] = {
                        "min": {"field": facet_data.value_location}
                    }
                    self._os_query.query["aggs"][facet_data.aggs_name_facet_max()] = {
                        "max": {"field": facet_data.value_location}
                    }
        return self


def aggs_facet(value_field, slug_field):
    return {
        # Limit to top 20 elements of the facet - https://thetower.atlassian.net/browse/ECMP-3843
        # Might change later as we learn
        "terms": {"field": value_field, "size": 10_000},
        "aggs": {
            "product_count": {"cardinality": {"field": "vtexProductId"}},
            # TODO: Add ordering on "slug" in case multiple values, take the most common one
            "slug": {"terms": {"field": slug_field}},
            # Sort values by product_count so most populous are first
            "product_count_sort": {
                "bucket_sort": {"sort": [{"product_count": {"order": "desc"}}]}
            },
        },
    }


def aggs_facet_count(value_field):
    return {"cardinality": {"field": value_field}}
