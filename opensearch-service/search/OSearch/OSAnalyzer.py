from search.OSearch.OS import os_connect


class OSAnalyzer:
    @staticmethod
    def keywords(text, index, field=None):
        params = {"text": text}
        if field is not None:
            params["field"] = field
        res = os_connect().indices.analyze(params, index=index)
        return {t["token"] for t in res["tokens"]}
