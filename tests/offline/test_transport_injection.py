"""Injecting a transport, and proving the seam fits a real second implementation.

The default transport is a ``requests.Session`` and nothing else. The reason
for the seam is the *other* implementation: a client that adds timeouts,
bounded retry, quota-header throttling, typed errors and redacted logging, and
that this library must know nothing about.

:class:`ApiClientTransportSketch` below is that second implementation, written
against the signature of the Dreambits platform's ``ApiClient`` and driven here
by a fake of it. It is a sketch, not the deliverable — the real adapter belongs
in ``dbt_bol_connector``, because this library must never import an Odoo addon
and the shared connector base must stay marketplace-agnostic. Its purpose here
is to prove the protocol is implementable by something that is not a session
before anybody depends on it.
"""

import unittest

from bol.retailer.api import RetailerAPI
from bol.retailer.transport import Transport, endpoint_group

from .support import RecordingTransport, make_response, response_from_fixture


class TestInjectedTransportTakesOverEverything(unittest.TestCase):
    def setUp(self):
        self.transport = RecordingTransport()
        self.api = RetailerAPI(transport=self.transport)

    def test_the_injected_transport_is_used_as_is(self):
        self.assertIs(self.api.transport, self.transport)

    def test_no_session_is_built_when_a_transport_is_given(self):
        # A transport that manages connections itself must not be shadowed by
        # a spare requests.Session nobody uses.
        self.assertFalse(hasattr(self.transport, "session"))
        with self.assertRaises(AttributeError) as caught:
            self.api.session
        self.assertIn("api.transport", str(caught.exception))

    def test_a_transport_need_not_subclass_the_protocol(self):
        self.assertNotIsInstance(self.transport, Transport)

    def test_requests_go_through_it_with_an_absolute_url(self):
        self.transport.responses.append(
            response_from_fixture("bol/orders_page_1.json")
        )
        self.api.orders.list(page=2)
        call = self.transport.call()
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["url"], "https://api.bol.com/retailer/orders")
        self.assertEqual(call["params"], {"page": 2})

    def test_a_body_and_headers_arrive_as_keywords(self):
        self.transport.responses.append(
            response_from_fixture("bol/process_status_submitted_shipment.json")
        )
        self.api.returns.handleReturnItem("rma-1", "RETURN_RECEIVED", 1)
        call = self.transport.call()
        self.assertEqual(call["method"], "PUT")
        self.assertEqual(
            call["json"],
            {"handlingResult": "RETURN_RECEIVED", "quantityReturned": 1},
        )

    def test_a_per_call_media_type_arrives_in_headers(self):
        self.transport.responses.append(
            response_from_fixture("bol/economic_operators.json")
        )
        self.api.economic_operators.list()
        self.assertEqual(
            self.transport.call()["headers"],
            {"Accept": "application/vnd.economic-operator.v1+json"},
        )

    def test_timeout_is_passed_as_none_so_the_transport_decides(self):
        self.transport.responses.append(
            response_from_fixture("bol/orders_page_1.json")
        )
        self.api.orders.list()
        self.assertIsNone(self.transport.call()["timeout"])

    def test_an_explicit_timeout_still_wins(self):
        transport = RecordingTransport(
            responses=[response_from_fixture("bol/orders_page_1.json")]
        )
        RetailerAPI(transport=transport, timeout=(5, 30)).orders.list()
        self.assertEqual(transport.call()["timeout"], (5, 30))

    def test_login_goes_through_it(self):
        token = self.api.login("client-id", "client-secret")
        self.assertEqual(
            self.transport.logins,
            [("https://login.bol.com", "client-id", "client-secret")],
        )
        self.assertEqual(token, self.transport.token)
        self.assertEqual(self.transport.access_tokens, ["recorded-token"])

    def test_set_access_token_goes_through_it(self):
        self.api.set_access_token("a-token")
        self.assertEqual(self.transport.access_tokens, ["a-token"])

    def test_a_raw_response_reader_still_gets_its_response(self):
        response = make_response(raw_body="ean,offerId\n1,2\n")
        self.transport.responses.append(response)
        self.assertIs(self.api.offers.getOffersFile("export-1"), response)


# ---------------------------------------------------------------------------
# The sketch handed to P2-3b
# ---------------------------------------------------------------------------


class FakeApiClient(object):
    """Stands in for ``dbt_base_connector.transport.client.ApiClient``.

    The signatures are copied from it verbatim, which is the only thing that
    makes this test worth anything: if the real client's surface changes, the
    sketch stops being a proof.
    """

    def __init__(self, base_url, responses=None, timeout=(5, 30)):
        self.base_url = base_url.rstrip("/")
        self.responses = list(responses or [])
        self.timeout = timeout
        self.calls = []
        self.closed = False

    def request(self, method, path, params=None, json=None, data=None,
                headers=None, media_type=None, timeout=None):
        self.calls.append(
            {
                "method": method,
                "path": path,
                "params": params,
                "json": json,
                "headers": headers,
                "media_type": media_type,
                "timeout": timeout,
            }
        )
        return self.responses.pop(0)

    def close(self):
        self.closed = True


class FakeClientCredentialsAuth(object):
    """Stands in for ``ClientCredentialsAuth``: it owns the token, not the caller."""

    DEFAULT_TOKEN = {
        "access_token": "auth-owned-token",
        "expires_in": 599,
        "scope": "retailer",
        "token_type": "Bearer",
    }

    def __init__(self, token=None):
        self.token = dict(self.DEFAULT_TOKEN) if token is None else token
        self.refreshes = 0

    def refresh(self):
        self.refreshes += 1
        return self.token


class ApiClientTransportSketch(object):
    """Implements the library's transport protocol over an ``ApiClient``.

    Two of the four methods are not doing what their names suggest, and both
    say so out loud rather than quietly succeeding:

    * ``login()`` does not log in — ``ClientCredentialsAuth`` already refreshes
      on expiry and on a 401 — but it is a *passthrough*, not a no-op: it asks
      the auth strategy for its token and returns it in the shape
      ``RetailerAPI.login`` expects. An auth strategy that cannot produce one
      raises rather than returning something falsy.
    * ``set_access_token()`` genuinely has nothing to do, because the auth
      strategy writes the ``Authorization`` header. It records a warning on the
      log sink so that a caller still driving tokens by hand finds out.
    """

    def __init__(self, client, auth, log=None):
        self.client = client
        self.auth = auth
        self.log = log
        self.ignored_tokens = []

    def request(self, method, url, params=None, json=None, headers=None,
                timeout=None, **kwargs):
        # The library builds an absolute URL; ApiClient._resolve_url passes an
        # absolute path straight through, so the two compose without either
        # side knowing about the other's base.
        return self.client.request(
            method,
            url,
            params=params,
            json=json,
            headers=headers,
            timeout=timeout,
            **kwargs
        )

    def login(self, login_url, client_id, client_secret):
        token = self.auth.refresh()
        if not token or "access_token" not in token:
            raise NotImplementedError(
                "This transport authenticates through the ApiClient's auth "
                "strategy, which did not return a token. Credentials come from "
                "the instance record, not from RetailerAPI.login()."
            )
        return token

    def set_access_token(self, access_token):
        self.ignored_tokens.append(access_token)
        if self.log is not None:
            self.log.warning(
                "set_access_token() ignored: this transport's auth strategy "
                "owns the Authorization header and refreshes it itself"
            )

    def close(self):
        self.client.close()


class RecordingLog(object):
    def __init__(self):
        self.warnings = []

    def warning(self, message, **context):
        self.warnings.append(message)


class TestTheSeamFitsAnApiClient(unittest.TestCase):
    """Prove the protocol against a real second implementation, not a hypothetical."""

    def build(self, *responses):
        self.client = FakeApiClient(
            "https://api.bol.com", responses=list(responses)
        )
        self.auth = FakeClientCredentialsAuth()
        self.log = RecordingLog()
        self.transport = ApiClientTransportSketch(
            self.client, self.auth, log=self.log
        )
        return RetailerAPI(transport=self.transport)

    def test_a_read_goes_through_the_client(self):
        api = self.build(response_from_fixture("bol/orders_page_1.json"))
        orders = api.orders.list(page=1)
        call = self.client.calls[0]
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["path"], "https://api.bol.com/retailer/orders")
        self.assertEqual(call["params"], {"page": 1})
        self.assertEqual(orders[0].orderId, "C000GUOJ8Q")

    def test_a_write_goes_through_the_client_with_its_body(self):
        api = self.build(
            response_from_fixture("bol/process_status_submitted_shipment.json")
        )
        api.orders.ship_order_item("9203065392", "SHIP-1")
        call = self.client.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["path"], "https://api.bol.com/retailer/shipments")
        self.assertEqual(call["json"]["shipmentReference"], "SHIP-1")

    def test_a_raw_response_is_not_parsed_on_the_way_back(self):
        # ApiClient.request returns a Response and parsing is the separate,
        # opt-in client.json(response). That is what keeps the CSV export and
        # the PDF labels working.
        response = make_response(raw_body="ean,offerId\n1,2\n")
        api = self.build(response)
        self.assertIs(api.offers.getOffersFile("export-1"), response)

    def test_the_urls_the_client_sees_group_into_separate_budgets(self):
        """The whole argument for exposing ``endpoint_group``.

        These are the five in-scope base paths as the *client* receives them.
        If they do not resolve to five groups, one quota overwrites another and
        the limiter spends budget it does not have.
        """
        api = self.build(
            response_from_fixture("bol/orders_page_1.json"),
            make_response(body={}),
            response_from_fixture("bol/returns_list.json"),
            response_from_fixture("bol/economic_operators.json"),
            response_from_fixture("bol/process_status_getbyids_success.json"),
        )
        api.orders.list()
        api.offers.getSingleOffer("offer-1")
        api.returns.get()
        api.economic_operators.list()
        api.process_status.getByIds(["one"])

        groups = [endpoint_group(call["path"]) for call in self.client.calls]
        self.assertEqual(
            groups,
            ["orders", "offers", "returns", "economic-operators", "process-status"],
        )
        self.assertEqual(len(set(groups)), 5)

    def test_login_is_a_passthrough_to_the_auth_strategy(self):
        api = self.build()
        token = api.login("ignored-id", "ignored-secret")
        self.assertEqual(token["access_token"], "auth-owned-token")
        self.assertEqual(self.auth.refreshes, 1)

    def test_login_raises_rather_than_pretending_when_it_cannot_authenticate(self):
        client = FakeApiClient("https://api.bol.com")
        auth = FakeClientCredentialsAuth(token={})
        api = RetailerAPI(transport=ApiClientTransportSketch(client, auth))
        with self.assertRaises(NotImplementedError):
            api.login("id", "secret")

    def test_set_access_token_is_loud_about_ignoring_the_token(self):
        api = self.build()
        api.set_access_token("a-token-nobody-will-use")
        self.assertEqual(
            self.transport.ignored_tokens, ["a-token-nobody-will-use"]
        )
        self.assertEqual(len(self.log.warnings), 1)
        self.assertIn("ignored", self.log.warnings[0])

    def test_close_reaches_the_client(self):
        api = self.build()
        api.transport.close()
        self.assertTrue(self.client.closed)


if __name__ == "__main__":
    unittest.main()
