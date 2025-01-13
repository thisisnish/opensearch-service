import json
import logging
from abc import ABC
from datetime import datetime

from search.OSearch.OSQuery import MultiQuery, QueryBuilder

logger = logging.getLogger("search:ParticipantQuery")

SortOrder = [
    "RELEVANCE",
]


class BaseQuery(ABC):
    def __init__(self, index_name: str) -> None:
        self.os_query = QueryBuilder(index_name)
        self.page_size = 20
        self.page_number = 1
        self.empty_query = True

    def set_page_size(self, size: int):
        self.page_size = size

    def set_page_number(self, number: int):
        self.page_number = number

    def format_multiquery_results(
        self, qlist, mquery_results: dict, client_duration: float
    ):
        results_count: int = len(mquery_results["responses"])

        if len(qlist) != results_count:
            raise ValueError("Results count does not match query count")  # noqa

        mq_result = {
            "client_duration_ms": client_duration,
            "opensearch_duration_ms": mquery_results["took"],
            "response_count": len(mquery_results["responses"]),
            "responses": [],
        }

        for index in range(results_count):
            query = qlist[index]["query"]
            result = mquery_results["responses"][index]

            page_size: int = int(query["size"])
            offset: int = int(query["from"])
            page_no: int = 1
            if offset > 0:
                page_no = int((offset / page_size) + 1)

            formatted_result = BaseQuery.format_results(
                query_s=json.dumps(query),
                search_results=result,
                page_no=page_no,
                page_size=page_size,
                client_duration=client_duration,
            )

            mq_result["responses"].append(formatted_result)

        return mq_result

    def format_results(
        query_s: str,
        search_results: dict,
        page_size: int,
        page_no: int,
        client_duration: float,
    ):
        results = search_results["hits"]["hits"]

        duration = int(search_results["took"])

        if (
            int(search_results["hits"]["total"]["value"]) > 1
            and search_results["hits"]["max_score"] is not None
        ):
            max_score = max(1.0, float(search_results["hits"]["max_score"]))
        else:
            max_score = 1.0

        results_src = []
        for res in results:
            res_score = (
                round((float(res["_score"]) / max_score) * 100, 2)
                if res["_score"] is not None
                else 1.0
            )
            res["_source"]["_score"] = res_score
            results_src.append(res["_source"])

        results_count = search_results["hits"]["total"]["value"]
        page_count = int(results_count / page_size)
        if results_count % page_size > 0:
            page_count = page_count + 1

        returned_results = results_src[:page_size]

        total_result = {
            "duration_ms": client_duration,
            "opensearch_duration": duration,
            "paging": {
                "total_records": results_count,
                "page_size": page_size,
                "total_page_count": page_count,
                "current_page_no": page_no,
                "current_page_size": len(returned_results),
            },
            "query": query_s,
            "results": returned_results,
        }

        return total_result

    def pre_process(self):
        self.os_query.paginate(self.page_size, self.page_number)

    def execute(self, page_no: int = -1, page_size: int = -1):
        if self.empty_query:
            self.os_query.must(QueryBuilder.match_all())

        if page_no > 0:
            self.page_number = page_no
        if page_size > 0:
            self.page_size = page_size

        self.pre_process()

        start_time: datetime = datetime.now()

        search_results = self.os_query.execute_search()

        end_time = datetime.now()
        duration = (end_time - start_time).microseconds / 1000

        return BaseQuery.format_results(
            query_s=json.dumps(self.os_query.query),
            search_results=search_results,
            client_duration=duration,
            page_size=page_size,
            page_no=page_no,
        )

    def execute_multiquery(multiquery: MultiQuery):
        start_time: datetime = datetime.now()
        search_results = multiquery.execute()
        end_time = datetime.now()
        duration = (end_time - start_time).microseconds / 1000

        results = BaseQuery.format_multiquery_results(
            mquery_results=search_results,
            qlist=multiquery.qlist,
            client_duration=duration,
        )

        return results
