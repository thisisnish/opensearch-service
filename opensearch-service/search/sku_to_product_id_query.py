import json

from search.OSearch.OSQuery import QueryBuilder
from util.envvar import STAGE
from util.logging import get_logger
from util.time import current_milli_time

log = get_logger("app")


class SkuToProductIdQuery:
    def __init__(self, index_name: str):
        self._os_query: QueryBuilder = QueryBuilder(index_name)
        self._os_query.return_fields(includes=["vtexProductId"])

    def sku_id_list(self, _sku_id_list: list[str]):
        self._os_query.filter({"terms": {"vtexSkuId": _sku_id_list}})

    def trade_policy(self, _trade_policy: str):
        self._os_query.filter({"terms": {"tradePolicy": [_trade_policy]}})

    def execute_search(self):
        print(json.dumps(self._os_query.query))
        os_start = current_milli_time()
        os_response = self._os_query.execute_search()
        log.info(
            {
                "stage": STAGE,
                "os_latency": current_milli_time() - os_start,
                "request_type": "sku_to_product_id",
            }
        )
        return os_response
