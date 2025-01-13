import json

from search.base_products_query import BaseProductQuery
from util.envvar import STAGE
from util.logging import get_logger
from util.time import current_milli_time

log = get_logger("app")


class ProductsSearchQuery(BaseProductQuery):
    def __init__(self, index_name):
        super().__init__(index_name)
        self.return_fields(
            includes=["vtexProductId", "tradePolicy", "productResult"],
            excludes=["productResult.priceRange"],
        )
        self.collapse_skus(
            [
                "vtexSkuId",
                "offerItemResult",
                "productSkuResult",
                "productResult.skuSpecifications",
            ]
        )
        return

    def execute_search(self):
        self.build()
        print(json.dumps(self._os_query.query))
        os_start = current_milli_time()
        os_response = self._os_query.execute_search()
        log.info(
            {
                "stage": STAGE,
                "os_latency": current_milli_time() - os_start,
                "request_type": "product_search",
            }
        )
        return os_response
