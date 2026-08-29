"""The defects fixed in 1.6.0 — and the one deliberately left alone.

Recorded as L1, L3, L4 and L5 in the connector project's ``bol_issues.md``.
"""

import unittest

import requests

from bol.retailer.api import RetailerAPI
from bol.retailer.models import ProcessStatus

from .support import StubSession, make_response, response_from_fixture


class DefectCase(unittest.TestCase):
    def api_for(self, *responses):
        self.session = StubSession(responses=list(responses))
        return RetailerAPI(session=self.session)

    def url(self, index=0):
        return self.session.url(index)


class TestL1TransportUpdateUrl(DefectCase):
    """``transports.update`` passed the id positionally into ``override_group``.

    ``MethodGroup.request(self, method, override_group=None, path="", ...)`` —
    the second positional argument is the *group*, so the URL came out as
    ``/retailer/{transport_id}`` and the word ``transports`` vanished. Latent:
    no addon calls it, so it would have failed on first use by whoever wired up
    transport updates, which is the worst moment to find out.
    """

    def test_the_transport_id_lands_in_the_path(self):
        api = self.api_for(
            response_from_fixture("bol/process_status_submitted_shipment.json")
        )
        status = api.transports.update("transport-1", "TNT", "3STOTA123")
        self.assertEqual(
            self.url(), "https://api.bol.com/retailer/transports/transport-1"
        )
        self.assertEqual(self.session.method(), "PUT")
        self.assertEqual(
            self.session.json(),
            {"transporterCode": "TNT", "trackAndTrace": "3STOTA123"},
        )
        self.assertIsInstance(status, ProcessStatus)

    def test_the_group_segment_is_not_the_transport_id(self):
        api = self.api_for(
            response_from_fixture("bol/process_status_submitted_shipment.json")
        )
        api.transports.update("transport-1", "TNT", "3STOTA123")
        self.assertNotEqual(
            self.url(), "https://api.bol.com/retailer/transport-1"
        )


class TestL3GuardsRaiseInsteadOfReturningSomethingUnusable(DefectCase):
    """One method group used to have three return types on its error paths.

    A guard that returns ``None``, ``{}`` or the *string*
    ``"{'error': 'Insufficient data provided'}"`` moves the failure somewhere
    else. The string is the worst of the three because it is truthy: a caller's
    ``if response:`` passes and the next line raises ``AttributeError`` in code
    that has nothing to do with the mistake.
    """

    def test_update_product_without_fulfilment_raises(self):
        api = self.api_for()
        with self.assertRaises(ValueError) as caught:
            api.offers.updateProduct("offer-1", {"referenceCode": "REF"})
        self.assertIn("fulfilment", str(caught.exception))
        self.assertEqual(self.session.call_count, 0)

    def test_update_product_no_longer_returns_a_truthy_error_string(self):
        api = self.api_for()
        try:
            result = api.offers.updateProduct("offer-1", {})
        except ValueError:
            return
        self.fail("expected ValueError, got %r" % (result,))

    def test_get_by_ids_with_a_non_list_raises(self):
        api = self.api_for()
        for bad in ("a-process-id", 42, {"processStatusId": "x"}, None):
            with self.assertRaises(ValueError) as caught:
                api.process_status.getByIds(bad)
            self.assertIn("process_ids", str(caught.exception))
        self.assertEqual(self.session.call_count, 0)

    def test_get_by_ids_still_accepts_an_empty_list(self):
        # Not a caller error, and the connector's poller can produce one.
        api = self.api_for(make_response(body={"processStatuses": []}))
        result = api.process_status.getByIds([])
        self.assertEqual(list(result), [])
        self.assertEqual(self.session.json(), {"processStatusQueries": []})

    def test_get_delivery_options_names_the_argument_at_fault(self):
        api = self.api_for()
        for bad in (None, "", {}, "not-a-list"):
            with self.assertRaises(ValueError) as caught:
                api.labels.getDeliveryOptions(bad)
            self.assertIn("orderitems_list", str(caught.exception))
        self.assertEqual(self.session.call_count, 0)

    def test_create_shipping_label_names_the_missing_label_id(self):
        api = self.api_for()
        with self.assertRaises(ValueError) as caught:
            api.labels.createShippingLabel([{"orderItemId": "1"}], None)
        self.assertIn("label_id", str(caught.exception))

    def test_create_shipping_label_names_the_missing_order_items(self):
        api = self.api_for()
        with self.assertRaises(ValueError) as caught:
            api.labels.createShippingLabel([], "label-offer-1")
        self.assertIn("orderitems_list", str(caught.exception))

    def test_every_insights_method_raises_on_a_missing_argument(self):
        api = self.api_for()
        cases = [
            ("getOfferInsights", ("", "DAY", 7, ["VIEWS"]), "offer_id"),
            ("getOfferInsights", ("o", "", 7, ["VIEWS"]), "period"),
            ("getOfferInsights", ("o", "DAY", None, ["VIEWS"]), "number_of_periods"),
            ("getOfferInsights", ("o", "DAY", 7, "VIEWS"), "name"),
            ("getPerformanceIndicators", (None, 2026, 35), "name"),
            ("getPerformanceIndicators", (["CANCELLATIONS"], None, 35), "year"),
            ("getPerformanceIndicators", (["CANCELLATIONS"], 2026, None), "week"),
            ("getProductRanks", (None, "2026-08-27"), "ean"),
            ("getProductRanks", ("8720849300131", None), "date"),
            ("getSalesForecast", (None, 4), "offer_id"),
            ("getSalesForecast", ("offer-1", None), "weeks_ahead"),
            ("getSearchTerms", (None, "WEEK", 4), "search_term"),
            ("getSearchTerms", ("bureaustoel", None, 4), "period"),
            ("getSearchTerms", ("bureaustoel", "WEEK", None), "number_of_periods"),
        ]
        for name, args, expected in cases:
            method = getattr(api.insights, name)
            with self.assertRaises(ValueError) as caught:
                method(*args)
            self.assertIn(expected, str(caught.exception), "%s%r" % (name, args))
        self.assertEqual(self.session.call_count, 0)

    def test_a_valid_insights_call_still_goes_through(self):
        api = self.api_for(make_response(body={"offerInsights": []}))
        api.insights.getOfferInsights("offer-1", "DAY", 7, ["PRODUCT_VISITS"])
        self.assertEqual(
            self.url(), "https://api.bol.com/retailer/insights/offer"
        )
        self.assertEqual(
            self.session.params(),
            {
                "offer-id": "offer-1",
                "period": "DAY",
                "number-of-periods": 7,
                "name": "PRODUCT_VISITS",
            },
        )

    def test_no_public_method_returns_none_on_a_guard_any_more(self):
        api = self.api_for()
        guarded = [
            (api.labels.getDeliveryOptions, (None,)),
            (api.labels.createShippingLabel, (None, None)),
            (api.insights.getOfferInsights, (None, None, None, None)),
            (api.insights.getPerformanceIndicators, (None, None, None)),
            (api.insights.getProductRanks, (None, None)),
            (api.insights.getSalesForecast, (None, None)),
            (api.insights.getSearchTerms, (None, None, None)),
        ]
        for method, args in guarded:
            self.assertRaises(ValueError, method, *args)


class TestL5TheSecretIsSentOnce(unittest.TestCase):
    """The client secret went out as HTTP Basic *and* in the form body."""

    def test_login_through_the_api_sends_no_secret_in_the_body(self):
        session = StubSession(
            post_responses=[response_from_fixture("bol/token_200.json")]
        )
        api = RetailerAPI(session=session)
        api.login("a-client-id", "a-client-secret")
        post = session.posts[0]
        self.assertEqual(post["auth"], ("a-client-id", "a-client-secret"))
        self.assertEqual(post["data"], {"grant_type": "client_credentials"})
        self.assertNotIn("a-client-secret", str(post["data"]))

    def test_the_grant_type_is_unchanged(self):
        session = StubSession(
            post_responses=[response_from_fixture("bol/token_200.json")]
        )
        RetailerAPI(session=session).login("id", "secret")
        self.assertEqual(
            session.posts[0]["data"]["grant_type"], "client_credentials"
        )


class TestL4LeftBrokenOnPurpose(unittest.TestCase):
    """``refresh_access_token`` is broken and stays broken until PM decides.

    bol.com's ``client_credentials`` grant issues no refresh token — the
    captured ``/token`` response is ``access_token``, ``expires_in``, ``scope``
    and ``token_type`` and nothing else — so the method posts a grant bol.com
    does not offer and then reads a key that is not in the reply. Whether the
    remedy is ``NotImplementedError`` (unfixable) or a fix (merely broken)
    depends on bol.com's own documentation, which nobody has read yet.

    These tests pin the current behaviour so that "still broken" stays a
    decision and does not quietly become an accident. Delete them with the
    decision, not before.
    """

    def test_it_still_exists_and_is_not_deprecated_away(self):
        self.assertTrue(callable(RetailerAPI.refresh_access_token))

    def test_it_still_refuses_when_there_is_no_refresh_token(self):
        api = RetailerAPI(session=StubSession())
        with self.assertRaises(ValueError):
            api.refresh_access_token("username", "password")

    def test_it_still_posts_the_grant_bol_does_not_offer(self):
        session = StubSession(
            post_responses=[response_from_fixture("bol/token_200.json")]
        )
        api = RetailerAPI(session=session, refresh_token="rt")
        # KeyError, because the captured reply carries no 'refresh_token'.
        with self.assertRaises(KeyError):
            api.refresh_access_token("username", "password")
        self.assertEqual(
            session.posts[0]["params"],
            {"grant_type": "refresh_token", "refresh_token": "rt"},
        )


class TestMutableDefaultsAreGone(DefectCase):
    """Ruff B006. Three signatures in this file shared one dict between calls."""

    def test_retailer_api_request_does_not_share_a_params_dict(self):
        api = self.api_for(make_response(body={}), make_response(body={}))
        api.request("GET", "/retailer/orders", {"page": 1})
        api.request("GET", "/retailer/orders")
        self.assertEqual(self.session.params(0), {"page": 1})
        self.assertEqual(self.session.params(1), {})

    def test_method_group_request_does_not_share_a_params_dict(self):
        api = self.api_for(make_response(body={}), make_response(body={}))
        api.orders.request("GET", params={"page": 1})
        api.orders.request("GET")
        self.assertEqual(self.session.params(0), {"page": 1})
        self.assertEqual(self.session.params(1), {})

    def test_a_caller_mutating_the_dict_it_passed_cannot_affect_the_next_call(self):
        api = self.api_for(make_response(body={}), make_response(body={}))
        params = {"page": 1}
        api.request("GET", "/retailer/orders", params)
        params["page"] = 2
        api.request("GET", "/retailer/orders")
        self.assertEqual(self.session.params(1), {})


class TestErrorsStillPropagate(DefectCase):
    """Nothing in the seam swallows a failure."""

    def test_an_http_error_reaches_the_caller(self):
        api = self.api_for(make_response(status=404, body={"e": "nope"}))
        with self.assertRaises(requests.HTTPError):
            api.orders.get("does-not-exist")

    def test_a_connection_error_reaches_the_caller(self):
        api = self.api_for(requests.ConnectionError("boom"))
        with self.assertRaises(requests.ConnectionError):
            api.orders.list()

    def test_a_truncated_body_raises_where_it_is_parsed(self):
        api = self.api_for(make_response(raw_body='{"orders": [{"orde'))
        self.assertRaises(ValueError, api.orders.list)


if __name__ == "__main__":
    unittest.main()
