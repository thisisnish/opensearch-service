from datetime import datetime, timedelta

import requests


class TimePersistedSession:
    def __init__(self, refresh_interval_hours=4):
        self.refresh_interval_hours = refresh_interval_hours
        self._session = requests.session()
        self._last_refresh = datetime.now()

    def get(self, url, **kwargs):
        if datetime.now() - self._last_refresh > timedelta(
            hours=self.refresh_interval_hours
        ):
            self._session.close()
            self._session = requests.session()
            self._last_refresh = datetime.now()
        return self._session.get(url, **kwargs, allow_redirects=True)

    def close(self):
        self._session.close()
