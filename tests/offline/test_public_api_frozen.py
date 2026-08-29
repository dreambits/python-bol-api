"""The public surface of ``RetailerAPI`` is frozen.

This package is on PyPI and is used outside the project that maintains it.
Adding the transport seam had to be *additive*: nothing removed, nothing
renamed, nothing given a new required argument, and the way a 1.5.0 user
constructs and authenticates the API unchanged.

If a test in this file fails, the question to ask is not "how do I update the
expectation" but "am I about to break somebody's code".
"""

import inspect
import unittest

import requests

from bol.retailer.api import MethodGroup, RetailerAPI
from bol.retailer.transport import RequestsTransport

from .support import StubSession, response_from_fixture

#: The signature every public callable had in 1.5.0, checked in so that the
#: next person to edit ``api.py`` finds out immediately. ``params={}`` became
#: ``params=None`` in 1.6.0 in three places (ruff B006, a mutable default) —
#: that is recorded here because it is a *default* change, which no caller can
#: observe, and not an argument change, which every caller could.
EXPECTED_SIGNATURES = {
    "RetailerAPI": {
        "login": "(self, client_id, client_secret)",
        "refresh_access_token": "(self, username, password, refresh_token=None)",
        "request": "(self, method, uri, params=None, **kwargs)",
        "set_access_token": "(self, access_token)",
    },
    "economic_operators": {
        "list": "(self)",
    },
    "insights": {
        "getOfferInsights": "(self, offer_id, period, number_of_periods, name)",
        "getPerformanceIndicators": "(self, name, year, week)",
        "getProductRanks": "(self, ean, date, type=None, page=1)",
        "getSalesForecast": "(self, offer_id, weeks_ahead)",
        "getSearchTerms": (
            "(self, search_term, period, number_of_periods, "
            "related_search_terms=None)"
        ),
    },
    "inventory": {
        "get": "(self, params=None)",
    },
    "invoices": {
        "get": "(self, invoice_id)",
        "get_specification": "(self, invoice_id, page=None)",
        "list": "(self, period_start=None, period_end=None)",
    },
    "labels": {
        "createShippingLabel": "(self, orderitems_list, label_id)",
        "getDeliveryOptions": "(self, orderitems_list)",
        "getShippingLabel": "(self, shipping_label_id)",
    },
    "offers": {
        "createSingleOffer": "(self, data)",
        "deleteOffers": "(self, offer_id)",
        "getOffersFile": "(self, export_id)",
        "getSingleOffer": "(self, offer_id)",
        "requestExportFile": "(self)",
        "updateProduct": "(self, offer_id, data)",
        "updateProductPrice": "(self, offer_id, data)",
        "updateProductStock": "(self, offer_id, data)",
    },
    "orders": {
        "cancel_order_item": "(self, order_item_id, reason_code)",
        "get": "(self, order_id)",
        "list": (
            "(self, fulfilment_method=None, page=None, status=None, "
            "change_interval_minute=None, latest_change_date=None, "
            "vvb_only=None)"
        ),
        "ship_order_item": (
            "(self, order_item_id, shipment_reference, shipping_label_id=None, "
            "transporter_code=None, track_and_trace=None, quantity=None)"
        ),
    },
    "process_status": {
        "get": "(self, entity_id, event_type, page=None)",
        "getById": "(self, process_id)",
        "getByIds": "(self, process_ids)",
    },
    "product_content": {
        "getValidationReport": "(self, uploadId)",
        "sendContent": "(self, language, content)",
    },
    "replenishments": {
        "create": "(self, params)",
        "get": "(self, **params)",
        "getById": "(self, replenishment_id)",
        "getLoadCarrierLabels": "(self, replenishment_id, label_type='WAREHOUSE')",
        "getPickList": "(self, replenishment_id)",
        "getProductLabels": "(self, labelFormat, products)",
        "getpickupTimeSlots": "(self, address, numberOfLoadCarriers)",
        "update": "(self, replenishment_id, **param)",
    },
    "returns": {
        "create_return": "(self, data)",
        "get": "(self, page=1, handled=False, fulfilment_method='FBR')",
        "getSingle": "(self, returnId)",
        "handleReturnItem": "(self, rmaId, status_reason, qty)",
    },
    "shipments": {
        "get": "(self, shipment_id)",
        "list": "(self, fulfilment_method=None, page=None, order_id=None)",
    },
    "transports": {
        "update": "(self, transport_id, transporter_code, track_and_trace)",
    },
}

#: ``RetailerAPI.__init__`` as it was in 1.5.0, in order. Anything after this
#: is new and must be optional.
INIT_PARAMETERS_1_5_0 = [
    "self",
    "test",
    "timeout",
    "session",
    "demo",
    "api_url",
    "login_url",
    "refresh_token",
]

#: The thirteen method groups, and the attribute each hangs off.
EXPECTED_GROUPS = {
    "economic_operators": "economic-operators",
    "insights": "insights",
    "inventory": "inventory",
    "invoices": "invoices",
    "labels": "shipping-labels",
    "offers": "offers",
    "orders": "orders",
    "process_status": "process-status",
    "product_content": "content",
    "replenishments": "replenishments",
    "returns": "returns",
    "shipments": "shipments",
    "transports": "transports",
}


def public_methods(obj):
    return {
        name: member
        for name, member in vars(type(obj)).items()
        if not name.startswith("_") and callable(member)
    }


class TestConstructionUnchanged(unittest.TestCase):
    """Acceptance 1: the 1.5.0 way of using this library still works."""

    def test_constructs_with_no_arguments_at_all(self):
        api = RetailerAPI()
        self.assertIsInstance(api.transport, RequestsTransport)
        self.assertIsInstance(api.session, requests.Session)

    def test_demo_construction_then_login_never_mentions_a_transport(self):
        # Byte for byte the 1.5.0 usage: construct, log in, call a method.
        # The only concession to the test is `session=`, which is a 1.5.0
        # argument and always was.
        session = StubSession(
            responses=[response_from_fixture("bol/orders_page_1.json")],
            post_responses=[response_from_fixture("bol/token_200.json")],
        )
        api = RetailerAPI(demo=True, session=session)
        token = api.login("a-client-id", "a-client-secret")

        self.assertEqual(token["access_token"], "REDACTED")
        self.assertEqual(token["expires_in"], 599)
        self.assertEqual(
            session.headers["Authorization"], "Bearer REDACTED"
        )
        self.assertEqual(
            session.headers["Accept"], "application/vnd.retailer.v10+json"
        )

        orders = api.orders.list()
        self.assertEqual(
            session.url(), "https://api.bol.com/retailer-demo/orders"
        )
        self.assertTrue(len(orders) > 0)

    def test_login_returns_the_token_document_unchanged(self):
        session = StubSession(
            post_responses=[response_from_fixture("bol/token_200.json")]
        )
        api = RetailerAPI(session=session)
        token = api.login("id", "secret")
        self.assertEqual(
            sorted(token),
            ["access_token", "expires_in", "scope", "token_type"],
        )

    def test_a_rejected_login_still_raises_http_error(self):
        session = StubSession(
            post_responses=[response_from_fixture("bol/token_401.json")]
        )
        api = RetailerAPI(session=session)
        with self.assertRaises(requests.HTTPError):
            api.login("id", "wrong-secret")

    def test_session_attribute_is_still_reachable_and_assignable(self):
        # The library's own online suite closes api.session in tearDown.
        api = RetailerAPI()
        self.assertIsInstance(api.session, requests.Session)
        replacement = StubSession()
        api.session = replacement
        self.assertIs(api.session, replacement)
        self.assertIs(api.transport.session, replacement)

    def test_timeout_and_api_url_keep_their_meaning(self):
        session = StubSession(responses=[response_from_fixture("bol/orders_page_1.json")])
        api = RetailerAPI(
            timeout=7, session=session, api_url="https://proxy.test"
        )
        api.orders.list()
        self.assertEqual(session.call()["timeout"], 7)
        self.assertEqual(session.url(), "https://proxy.test/retailer/orders")

    def test_test_and_refresh_token_arguments_still_accepted(self):
        api = RetailerAPI(test=True, refresh_token="rt")
        self.assertEqual(api.refresh_token, "rt")


class TestSignaturesFrozen(unittest.TestCase):
    """Acceptance 2: no public name removed, renamed or newly required."""

    def setUp(self):
        self.api = RetailerAPI()

    def test_init_keeps_the_1_5_0_parameters_in_order(self):
        parameters = list(
            inspect.signature(RetailerAPI.__init__).parameters
        )
        self.assertEqual(
            parameters[: len(INIT_PARAMETERS_1_5_0)], INIT_PARAMETERS_1_5_0
        )

    def test_every_parameter_added_since_1_5_0_is_optional_and_trailing(self):
        signature = inspect.signature(RetailerAPI.__init__)
        added = list(signature.parameters)[len(INIT_PARAMETERS_1_5_0):]
        self.assertEqual(added, ["transport"])
        for name in added:
            self.assertIsNot(
                signature.parameters[name].default,
                inspect.Parameter.empty,
                "%s must have a default; a public constructor cannot grow a "
                "required argument" % name,
            )

    def test_all_thirteen_method_groups_are_present(self):
        for attribute, group in sorted(EXPECTED_GROUPS.items()):
            member = getattr(self.api, attribute, None)
            self.assertIsInstance(
                member, MethodGroup, "api.%s is missing" % attribute
            )
            self.assertEqual(member.group, group)
        self.assertEqual(len(EXPECTED_GROUPS), 13)

    def test_public_signatures_match_the_checked_in_list(self):
        actual = {}
        for name, member in public_methods(self.api).items():
            actual[name] = str(inspect.signature(member))
        self.assertEqual(actual, EXPECTED_SIGNATURES["RetailerAPI"])

        for attribute in sorted(EXPECTED_GROUPS):
            group = getattr(self.api, attribute)
            actual = {
                name: str(inspect.signature(member))
                for name, member in public_methods(group).items()
            }
            self.assertEqual(
                actual,
                EXPECTED_SIGNATURES[attribute],
                "the public surface of api.%s changed" % attribute,
            )

    def test_no_public_method_disappeared(self):
        for attribute, expected in EXPECTED_SIGNATURES.items():
            owner = (
                self.api
                if attribute == "RetailerAPI"
                else getattr(self.api, attribute)
            )
            for name in expected:
                self.assertTrue(
                    callable(getattr(owner, name, None)),
                    "%s.%s was removed or renamed" % (attribute, name),
                )


if __name__ == "__main__":
    unittest.main()
