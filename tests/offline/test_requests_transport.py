"""``RequestsTransport`` is the old behaviour, moved.

Every assertion here describes something ``RetailerAPI`` did before the seam
existed. The class exists to guarantee there was no behaviour change for the
public, so these tests are the guarantee.

The one deliberate exception is the login body — see :class:`TestLogin`.
"""

import unittest

import requests

from bol.retailer.transport import RequestsTransport, Transport

from .support import StubSession, make_response, response_from_fixture


class TestSessionSetup(unittest.TestCase):
    def test_builds_its_own_session_when_none_is_given(self):
        transport = RequestsTransport()
        self.assertIsInstance(transport.session, requests.Session)

    def test_pins_accept_json_on_the_session(self):
        session = StubSession()
        RequestsTransport(session=session)
        self.assertEqual(session.headers["Accept"], "application/json")

    def test_pins_accept_on_a_session_the_caller_supplied(self):
        # 1.5.0 did this too: the header went on whichever session it was given.
        session = StubSession()
        session.headers["Accept"] = "text/plain"
        RequestsTransport(session=session)
        self.assertEqual(session.headers["Accept"], "application/json")

    def test_close_closes_the_session(self):
        session = StubSession()
        RequestsTransport(session=session).close()
        self.assertTrue(session.closed)


class TestRequest(unittest.TestCase):
    def setUp(self):
        self.session = StubSession()
        self.transport = RequestsTransport(session=self.session, timeout=11)

    def test_passes_method_url_and_params_straight_through(self):
        self.session.queue(make_response())
        self.transport.request(
            "GET", "https://api.bol.com/retailer/orders", params={"page": 2}
        )
        call = self.session.call()
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["url"], "https://api.bol.com/retailer/orders")
        self.assertEqual(call["params"], {"page": 2})

    def test_missing_params_become_an_empty_dict(self):
        self.session.queue(make_response())
        self.transport.request("GET", "https://api.bol.com/retailer/orders")
        self.assertEqual(self.session.call()["params"], {})

    def test_uses_its_configured_timeout_when_the_call_gives_none(self):
        self.session.queue(make_response())
        self.transport.request("GET", "https://api.bol.com/x")
        self.assertEqual(self.session.call()["timeout"], 11)

    def test_a_per_call_timeout_wins(self):
        self.session.queue(make_response())
        self.transport.request("GET", "https://api.bol.com/x", timeout=2)
        self.assertEqual(self.session.call()["timeout"], 2)

    def test_a_json_body_gets_the_retailer_content_type(self):
        self.session.queue(make_response())
        self.transport.request("POST", "https://api.bol.com/x", json={"a": 1})
        self.assertEqual(
            self.session.headers_sent()["content-type"],
            "application/vnd.retailer.v10+json",
        )

    def test_a_json_body_keeps_the_caller_s_own_headers(self):
        self.session.queue(make_response())
        self.transport.request(
            "POST",
            "https://api.bol.com/x",
            json={"a": 1},
            headers={"accept": "application/vnd.retailer.v10+pdf"},
        )
        sent = self.session.headers_sent()
        self.assertEqual(sent["accept"], "application/vnd.retailer.v10+pdf")
        self.assertEqual(
            sent["content-type"], "application/vnd.retailer.v10+json"
        )

    def test_the_caller_s_header_dict_is_not_mutated(self):
        self.session.queue(make_response())
        headers = {"accept": "application/vnd.retailer.v10+pdf"}
        self.transport.request(
            "POST", "https://api.bol.com/x", json={"a": 1}, headers=headers
        )
        self.assertEqual(
            headers, {"accept": "application/vnd.retailer.v10+pdf"}
        )

    def test_no_json_body_means_no_content_type_and_no_json_kwarg(self):
        self.session.queue(make_response())
        self.transport.request("GET", "https://api.bol.com/x")
        self.assertNotIn("json", self.session.call())
        self.assertEqual(self.session.headers_sent(), {})

    def test_an_explicit_json_none_is_still_a_json_body(self):
        # 1.5.0 keyed on the presence of the kwarg, not on its value.
        self.session.queue(make_response())
        self.transport.request("POST", "https://api.bol.com/x", json=None)
        self.assertIn("json", self.session.call())
        self.assertEqual(
            self.session.headers_sent()["content-type"],
            "application/vnd.retailer.v10+json",
        )

    def test_returns_the_response_object_itself(self):
        response = make_response(raw_body="ean,offerId\n123,abc\n")
        self.session.queue(response)
        self.assertIs(
            self.transport.request("GET", "https://api.bol.com/x"), response
        )

    def test_raises_for_an_error_status(self):
        self.session.queue(make_response(status=500, body={"e": 1}))
        with self.assertRaises(requests.HTTPError):
            self.transport.request("GET", "https://api.bol.com/x")

    def test_a_connection_failure_propagates(self):
        self.session.queue(requests.ConnectionError("no route to host"))
        with self.assertRaises(requests.ConnectionError):
            self.transport.request("GET", "https://api.bol.com/x")

    def test_a_timeout_propagates(self):
        self.session.queue(requests.Timeout("read timed out"))
        with self.assertRaises(requests.Timeout):
            self.transport.request("GET", "https://api.bol.com/x")

    def test_unknown_keywords_reach_the_session(self):
        # 1.5.0 forwarded **kwargs to session.request untouched.
        self.session.queue(make_response())
        self.transport.request(
            "GET", "https://api.bol.com/x", allow_redirects=False
        )
        self.assertIs(self.session.call()["allow_redirects"], False)


class TestLogin(unittest.TestCase):
    def setUp(self):
        self.session = StubSession(
            post_responses=[response_from_fixture("bol/token_200.json")]
        )
        self.transport = RequestsTransport(session=self.session)

    def test_posts_to_the_token_endpoint(self):
        self.transport.login("https://login.bol.com", "id", "secret")
        self.assertEqual(
            self.session.posts[0]["url"], "https://login.bol.com/token"
        )

    def test_sends_the_credentials_as_http_basic(self):
        self.transport.login("https://login.bol.com", "id", "secret")
        self.assertEqual(self.session.posts[0]["auth"], ("id", "secret"))

    def test_the_secret_is_not_also_in_the_form_body(self):
        """L5. Bol's documented grant is Basic; the body copy was redundant.

        Every place a secret appears is a place something can log it, and a
        proxy or debug hook that knows to redact ``Authorization`` does not
        know to redact a form field.
        """
        self.transport.login("https://login.bol.com", "id", "the-secret")
        body = self.session.posts[0]["data"]
        self.assertEqual(body, {"grant_type": "client_credentials"})
        self.assertNotIn("client_secret", body)
        self.assertNotIn("client_id", body)
        self.assertNotIn("the-secret", str(body))

    def test_returns_the_parsed_token(self):
        token = self.transport.login("https://login.bol.com", "id", "secret")
        self.assertEqual(token["access_token"], "REDACTED")

    def test_raises_on_a_rejected_login(self):
        session = StubSession(
            post_responses=[response_from_fixture("bol/token_401.json")]
        )
        with self.assertRaises(requests.HTTPError):
            RequestsTransport(session=session).login(
                "https://login.bol.com", "id", "wrong"
            )


class TestSetAccessToken(unittest.TestCase):
    def test_pins_bearer_and_the_retailer_media_type(self):
        session = StubSession()
        RequestsTransport(session=session).set_access_token("abc123")
        self.assertEqual(session.headers["Authorization"], "Bearer abc123")
        self.assertEqual(
            session.headers["Accept"], "application/vnd.retailer.v10+json"
        )


class TestProtocolIsDocumentation(unittest.TestCase):
    def test_the_default_transport_implements_the_protocol(self):
        for name in ("request", "login", "set_access_token", "close"):
            self.assertTrue(hasattr(Transport, name))
            self.assertTrue(callable(getattr(RequestsTransport, name)))

    def test_the_protocol_itself_refuses_to_pretend_it_works(self):
        transport = Transport()
        self.assertRaises(NotImplementedError, transport.close)
        self.assertRaises(
            NotImplementedError, transport.set_access_token, "t"
        )


if __name__ == "__main__":
    unittest.main()
