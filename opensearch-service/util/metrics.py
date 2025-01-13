import newrelic.agent

from util.envvar import is_prod


def record_metric(name: str, value: float):
    if is_prod():
        newrelic.agent.record_custom_metric(name, value)
