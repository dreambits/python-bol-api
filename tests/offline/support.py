"""Test doubles for the offline suite.

HTTP is faked at the ``requests.Session`` boundary and nowhere else:
:class:`StubSession` hands back genuine :class:`requests.Response` objects, so
``.text``, ``.json()``, ``.headers``, ``.status_code`` and
``.raise_for_status()`` behave exactly as they will in production. No socket is
opened by anything in this package.

Adapted from the Dreambits connector platform's
``dbt_base_connector/transport/tests/support.py``, which fakes the same
boundary for the same reason. The two are deliberately alike; this copy exists
so the library's tests depend on nothing but ``requests``.
"""

import json as json_module
import os

import requests
from requests.structures import CaseInsensitiveDict

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load_fixture(name):
    """Load an HTTP-shaped fixture: ``{"status", "headers", "body"}``."""
    with open(os.path.join(FIXTURE_DIR, name), "rb") as handle:
        return json_module.loads(handle.read().decode("utf-8"))


def make_response(status=200, body=None, headers=None,
                  url="https://api.bol.com/x", method="GET", raw_body=None):
    """Build a real ``requests.Response``."""
    response = requests.Response()
    response.status_code = status
    response.url = url
    response.headers = CaseInsensitiveDict(headers or {})
    response.encoding = "utf-8"
    if raw_body is not None:
        content = raw_body
    elif body is None:
        content = ""
    else:
        content = json_module.dumps(body)
    response._content = content.encode("utf-8")
    request = requests.PreparedRequest()
    request.method = method
    request.url = url
    response.request = request
    return response


def response_from_fixture(name, **overrides):
    """A ``requests.Response`` built from a fixture file.

    The fixtures' ``_note`` and ``_source`` keys are metadata for a human and
    are ignored here.
    """
    data = load_fixture(name)
    data.update(overrides)
    return make_response(
        status=data.get("status", 200),
        body=data.get("body"),
        headers=data.get("headers"),
        raw_body=data.get("raw_body"),
    )


def fixture_body(name):
    """The decoded body of a fixture, for asserting against what was parsed."""
    return load_fixture(name).get("body")


class StubSession(object):
    """Stands in for ``requests.Session``.

    ``responses`` is consumed in order by :meth:`request`; an entry that is an
    exception instance is raised rather than returned, which is how a
    connection failure is simulated. :meth:`post` has its own queue because the
    only thing that calls it is the login, and a test that queues a token
    response should not have to care where in the request order it lands.
    """

    def __init__(self, responses=None, post_responses=None):
        self.headers = CaseInsensitiveDict()
        self.responses = list(responses or [])
        self.post_responses = list(post_responses or [])
        self.calls = []
        self.posts = []
        self.closed = False

    def queue(self, *responses):
        self.responses.extend(responses)
        return self

    def queue_post(self, *responses):
        self.post_responses.extend(responses)
        return self

    def request(self, **kwargs):
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError(
                "StubSession ran out of responses on call %d: %s %s"
                % (len(self.calls), kwargs.get("method"), kwargs.get("url"))
            )
        result = self.responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    def post(self, url, **kwargs):
        call = dict(kwargs)
        call["url"] = url
        self.posts.append(call)
        if not self.post_responses:
            raise AssertionError("StubSession ran out of post responses")
        result = self.post_responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    def close(self):
        self.closed = True

    # -- assertion helpers -------------------------------------------------

    @property
    def call_count(self):
        return len(self.calls)

    def call(self, index=0):
        return self.calls[index]

    def url(self, index=0):
        return self.calls[index]["url"]

    def method(self, index=0):
        return self.calls[index]["method"]

    def params(self, index=0):
        return self.calls[index].get("params") or {}

    def json(self, index=0):
        return self.calls[index].get("json")

    def headers_sent(self, index=0):
        return CaseInsensitiveDict(self.calls[index].get("headers") or {})


class RecordingTransport(object):
    """A transport that records instead of transporting.

    Duck-typed on purpose: it does **not** subclass
    :class:`bol.retailer.transport.Transport`, because the library must accept
    anything with the four methods. It is also the stand-in for the adapter
    ``dbt_bol_connector`` will write over ``ApiClient`` — its ``request``
    signature is the one ``ApiClient.request`` already has.
    """

    def __init__(self, responses=None, token=None):
        self.responses = list(responses or [])
        self.token = token or {"access_token": "recorded-token", "expires_in": 599}
        self.calls = []
        self.logins = []
        self.access_tokens = []
        self.closed = False

    def request(self, method, url, params=None, json=None, headers=None,
                timeout=None, **kwargs):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "params": params,
                "json": json,
                "headers": headers,
                "timeout": timeout,
                "extra": kwargs,
            }
        )
        if not self.responses:
            raise AssertionError(
                "RecordingTransport ran out of responses on call %d: %s %s"
                % (len(self.calls), method, url)
            )
        result = self.responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    def login(self, login_url, client_id, client_secret):
        self.logins.append((login_url, client_id, client_secret))
        return self.token

    def set_access_token(self, access_token):
        self.access_tokens.append(access_token)

    def close(self):
        self.closed = True

    # -- assertion helpers -------------------------------------------------

    @property
    def call_count(self):
        return len(self.calls)

    def call(self, index=0):
        return self.calls[index]
