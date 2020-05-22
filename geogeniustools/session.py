import os
import requests

from geogeniustools.rda.env_variable import USER_ENDPOINT
from geogeniustools.rda.error import AkSkNotFound


def get_session():
    if os.environ.get("ACCESS_KEY", None) and os.environ.get("SECRET_KEY", None):
        return GeogeniusSession(access_key=os.environ.get("ACCESS_KEY"), secret_key=os.environ.get("SECRET_KEY"))
    else:
        raise AkSkNotFound("ACCESS_KEY or SECRET_KEY not set in environment")


class GeogeniusSession:

    def __init__(self, client=requests, token=None, access_key=None, secret_key=None):
        self._client = client
        self.token = token
        self.access_key = access_key
        self.secret_key = secret_key
        self.check_token_url = "{}/users/credentials".format(USER_ENDPOINT)
        self.refresh_token_url = "{}/users/credentials/login".format(USER_ENDPOINT)

    def _add_token(self, headers=None):
        """add token in headers"""
        if headers:
            headers['X-Auth-Token'] = self.token
        else:
            headers = {'X-Auth-Token': self.token}
        return headers

    def _check_token_valid(self):
        """check token is valid"""
        headers = self._add_token()
        res = self._client.get(self.check_token_url, headers=headers)
        return False if res.status_code != 200 else True

    def _refresh_token(self):
        headers = {"Content-Type": "application/json"}
        data = {"ak": self.access_key, "sk": self.secret_key}
        res = self._client.post(self.refresh_token_url, headers=headers, json=data)
        res.raise_for_status()
        self.token = res.json()["token"]

    def get_token(self):
        """Return a valid token"""
        if not self._check_token_valid():
            self._refresh_token()
        return self.token

    def _add_valid_token(self, headers):
        """check token is valid, if valid, add token in headers, if not, refresh token and add"""
        if not self._check_token_valid():
            self._refresh_token()
        return self._add_token(headers=headers)

    def request(self, url, method="get", data=None, json=None, headers=None, **kwargs):
        headers = self._add_valid_token(headers)
        return self._client.request(method, url, data=data, json=json, headers=headers, **kwargs)

    def get(self, url, **kwargs):
        return self.request(url, method="get", **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        return self.request(url, method="post", data=data, json=json, **kwargs)

    def delete(self, url,  data=None, json=None, **kwargs):
        return self.request(url, method="delete",  data=None, json=None, **kwargs)

    def put(self, url,  data=None, json=None, **kwargs):
        return self.request(url, method="put",  data=None, json=None, **kwargs)
