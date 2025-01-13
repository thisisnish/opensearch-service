import copy
import json
import logging
from typing import Any, List

from django.conf import settings

from search.OSearch.OS import os_connect

logger = logging.getLogger("opensearch")


class OS:
    def __init__(self):
        self.client = os_connect()


class QueryBuilder:
    def __init__(self, index):
        self.index = index
        self.query = {"query": {}}

    def paginate(self, page_size: int, page_number: int):
        self.query["from"] = (page_number - 1) * page_size
        self.query["size"] = page_size

    def return_fields(self, includes: List[str] = [], excludes: List[str] = []):
        if "_source" not in self.query:
            self.query["_source"] = {}
        if includes:
            self.query["_source"]["includes"] = includes
        if excludes:
            self.query["_source"]["excludes"] = excludes

    @classmethod
    def match_all(cls):
        return {"match_all": {}}

    @classmethod
    def equals(cls, field: str, value: Any):
        """exact value match (best with numbers, keywords, )"""
        filter_type = "term"
        if (
            bool(value)
            and not isinstance(value, str)
            and all(isinstance(elem, str) for elem in value)
            and value.__len__() > 0
        ):
            filter_type = "terms"

        query = {}
        match filter_type:
            case "term":
                query = {
                    filter_type: {
                        field: {
                            "value": value,
                        }
                    }
                }
            case _:
                query = {
                    filter_type: {
                        field: value,
                    }
                }

        return query

    @classmethod
    def fulltext(
        cls,
        match_field: str,
        text_string: str,
        boost: float,
        fuzziness: float,
        mode: str,
    ):
        """fuzzy search"""
        query = {}

        if mode.lower() == "adv":
            query = {
                "query_string": {
                    "query": text_string,
                    "default_field": match_field,
                }
            }
            if fuzziness and fuzziness > 0.0:
                query["query_string"]["fuzziness"] = fuzziness
            if boost and boost > 0.0:
                query["query_string"]["boost"] = boost
            return query

        query = {"match": {match_field: {"query": text_string}}}
        if fuzziness and fuzziness > 0.0:
            query["match"][match_field]["fuzziness"] = fuzziness
        if boost and boost > 0.0:
            query["match"][match_field]["boost"] = boost
        return query

    @classmethod
    def fulltext_multifield(
        cls,
        search_fields: List[str],
        text_string: str,
        fuzziness: float | str,
        mode: str,
        operator: str = "and",
        fuzziness_prefix_length: int = None,
        boost: float = None,
    ):
        """multi-field fuzzy search"""
        query = {}

        if mode == "adv":
            query = {"query_string": {"query": text_string, "fields": search_fields}}
            if fuzziness and (fuzziness > 0.0 or isinstance(fuzziness, str)):
                query["query_string"]["fuzziness"] = fuzziness
            return query

        query = {
            "multi_match": {
                "query": text_string,
                "operator": operator,
                "type": "most_fields",
            }
        }
        if search_fields:
            query["multi_match"]["fields"] = search_fields
        if fuzziness and (isinstance(fuzziness, str) or fuzziness > 0.0):
            query["multi_match"]["fuzziness"] = fuzziness
        if fuzziness_prefix_length:
            query["multi_match"]["prefix_length"] = fuzziness_prefix_length
        if boost is not None:
            query["multi_match"]["boost"] = boost
        return query

    @classmethod
    def range(
        cls,
        field: str,
        min_value: Any,
        min_inclusive: bool,
        max_value: Any,
        max_inclusive: bool,
        boost_value: float,
    ):
        """ranges of dates or numbers"""
        query = {"range": {field: {}}}
        if min_value:
            if min_inclusive and min_inclusive is True:
                query["range"][field]["gte"] = min_value
            else:
                query["range"][field]["gt"] = min_value
        if max_value:
            if max_inclusive and max_inclusive is True:
                query["range"][field]["lte"] = max_value
            else:
                query["range"][field]["lt"] = max_value
        if boost_value and boost_value > 0.0:
            query["range"][field]["boost"] = boost_value
        return query

    @classmethod
    def auto_suggest(cls, field: str, text: str):
        return {
            "multi_match": {
                "query": text,
                "type": "bool_prefix",
                "fields": [
                    field,
                    f"{field}._2gram",
                    f"{field}._3gram",
                ],
            }
        }

    @classmethod
    def location_radius(cls, field: str, geo_hash: str, radius_km: float):
        query = {"geo_distance": {"distance": f"{radius_km}km", field: str(geo_hash)}}
        return query

    @classmethod
    def location_point(cls, field: str, geo_coords: List[float]):
        query = {
            "geo_shape": {
                field: {
                    "shape": {"type": "point", "coordinates": geo_coords},
                    "relation": "intersects",
                }
            }
        }
        return query

    @classmethod
    def proximity_boost(cls, field: str, pivot: str, origin: any, boost: float = 1.0):
        query = {
            "distance_feature": {
                "field": field,
                "pivot": pivot,
                "origin": origin,
                "boost": boost,
            }
        }
        return query

    def must(self, filter: dict):
        if "bool" not in self.query["query"]:
            self.query["query"]["bool"] = {}
        if "must" not in self.query["query"]["bool"]:
            self.query["query"]["bool"]["must"] = []
        self.query["query"]["bool"]["must"].append(filter)

    def should(self, filter: dict):
        if "bool" not in self.query["query"]:
            self.query["query"]["bool"] = {}
        if "should" not in self.query["query"]["bool"]:
            self.query["query"]["bool"]["should"] = []
        self.query["query"]["bool"]["should"].append(filter)

    def must_not(self, filter: dict):
        if "bool" not in self.query["query"]:
            self.query["query"]["bool"] = {}
        if "not" not in self.query["query"]["bool"]:
            self.query["query"]["bool"]["not"] = []
        self.query["query"]["bool"]["not"].append(filter)

    def filter(self, filter: dict):
        if "bool" not in self.query["query"]:
            self.query["query"]["bool"] = {}
        if "filter" not in self.query["query"]["bool"]:
            self.query["query"]["bool"]["filter"] = []
        self.query["query"]["bool"]["filter"].append(filter)

    def sort(self, field: str, order: str):
        if "sort" not in self.query:
            self.query["sort"] = []
        self.query["sort"].append({field: {"order": order}})

    def collapse(self, field: str, inner_hits=None):
        self.query["collapse"] = {"field": field}
        if inner_hits is not None:
            self.query["collapse"]["inner_hits"] = inner_hits
        if "aggs" not in self.query:
            self.query["aggs"] = {}
        self.query["aggs"]["result_count"] = {"cardinality": {"field": field}}

    def geo_sort(self, ref_point: List[float], ref_field: str, order: str):
        if "sort" not in self.query:
            self.query["sort"] = []
        self.query["sort"].append(
            {"_geo_distance": {ref_field: ref_point, "order": order}}
        )

    def execute_search(self):
        return OS().client.search(index=self.index, body=self.query)


class MultiQuery:
    def __init__(self):
        self.qlist = []
        self.pagination_props = []
        self.sorts = []
        self.relevance_thresholds = []
        self.params = []
        self.buffer = ""

    def append_query(
        self,
        query_builder: QueryBuilder,
        index,
        pagination_props: dict,
        sort_order: str,
        relevance_threshold: int = settings.RELEVANCE_THRESHOLD,
        parameters: dict = {},
    ):
        doc_entry = {"index": index}
        self.buffer += json.dumps(doc_entry) + "\n"

        self.buffer += (
            json.dumps(query_builder.query, default=str).replace("\n", "") + "\n"
        )

        self.qlist.insert(
            self.qlist.__len__(),
            {
                "query": copy.deepcopy(query_builder.query),
            },
        )

        self.pagination_props.insert(self.pagination_props.__len__(), pagination_props)

        self.sorts.insert(self.sorts.__len__(), sort_order)

        self.relevance_thresholds.insert(
            self.relevance_thresholds.__len__(), relevance_threshold
        )

        self.params.insert(self.params.__len__(), parameters)

    def execute(self):
        for query in self.qlist:
            if query["query"]["query"] == {}:
                raise ValueError("One of the queries is not formed correctly.")
        results = os_connect().msearch(body=self.buffer)
        return results
