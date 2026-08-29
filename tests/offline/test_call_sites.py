"""Every call site the Bol connector makes, exercised without a network.

The three Bol addons make 33 calls into this library across eight of its
thirteen method groups. All thirty-three go through ``RetailerAPI.request()``,
so replacing what sits behind that one method migrates them at once — which
means the only way to know they still work is to call them.

* the 20 in-scope sites (``dbt_bol_connector``) are covered method by method;
* the 13 out-of-scope sites (``dbt_bol_fbb``, ``dbt_bol_vvb``) are covered
  because those addons must keep working *without being edited*;
* the five raw-``Response`` readers get their own class, because returning a
  parsed model from any of them would break a CSV or PDF download and the
  mistake is an easy one to make.

The five method groups nothing calls — ``shipments``, ``invoices``,
``transports``, ``insights``, ``product_content`` — are deliberately not
covered here beyond their defect tests. They are not this project's problem.
"""

import unittest
from decimal import Decimal

from bol.retailer.api import RetailerAPI
from bol.retailer.models import (
    EconomicOperators,
    Inventories,
    Offer,
    OffersResponse,
    Order,
    Orders,
    ProcessStatus,
    ProcessStatuses,
    Replenishment,
    Replenishments,
    ReturnItems,
    ShippingLabels,
    SingleReturnItem,
    TimeSlots,
)

from .support import StubSession, make_response, response_from_fixture


class CallSiteCase(unittest.TestCase):
    """Builds an API over a stub session and exposes the recorded call."""

    demo = False

    def api_for(self, *responses):
        self.session = StubSession(responses=list(responses))
        return RetailerAPI(demo=self.demo, session=self.session)

    def api_for_fixture(self, name):
        return self.api_for(response_from_fixture(name))

    def api_for_body(self, body, **kw):
        return self.api_for(make_response(body=body, **kw))

    # -- assertions --------------------------------------------------------

    def assertCalled(self, method, path, index=0):
        call = self.session.call(index)
        self.assertEqual(call["method"], method)
        self.assertEqual(call["url"], "https://api.bol.com" + path)

    def assertParams(self, expected, index=0):
        self.assertEqual(self.session.params(index), expected)

    def assertJson(self, expected, index=0):
        self.assertEqual(self.session.json(index), expected)


# ---------------------------------------------------------------------------
# In scope: dbt_bol_connector, 20 call sites, five groups
# ---------------------------------------------------------------------------


class TestOrders(CallSiteCase):
    def test_list_no_arguments(self):
        api = self.api_for_fixture("bol/orders_page_1.json")
        orders = api.orders.list()
        self.assertCalled("GET", "/retailer/orders")
        self.assertParams({})
        self.assertIsInstance(orders, Orders)
        self.assertEqual(orders[0].orderId, "C000GUOJ8Q")

    def test_list_with_every_filter(self):
        api = self.api_for_fixture("bol/orders_page_1.json")
        api.orders.list(
            fulfilment_method="FBB",
            page=2,
            status="ALL",
            change_interval_minute=30,
            latest_change_date="2026-08-27",
            vvb_only=False,
        )
        self.assertParams(
            {
                "fulfilment-method": "FBB",
                "page": 2,
                "status": "ALL",
                "change-interval-minute": 30,
                "latest-change-date": "2026-08-27",
                "vvb-only": "false",
            }
        )

    def test_list_page_one_is_sent_explicitly(self):
        # `page=1` is falsy-adjacent and the guard is `is not None`; a page 1
        # that silently vanished would be a paging bug hiding in plain sight.
        api = self.api_for_fixture("bol/orders_page_1.json")
        api.orders.list(page=1)
        self.assertParams({"page": 1})

    def test_list_of_an_exhausted_page_parses_to_nothing(self):
        # Captured evidence: a page past the end is 200 with `{}` and the
        # collection key absent, not an empty list.
        api = self.api_for_fixture("bol/orders_page_empty.json")
        orders = api.orders.list(page=99)
        self.assertEqual(list(orders), [])

    def test_get(self):
        api = self.api_for_fixture("synthetic/order_single.json")
        order = api.orders.get("C000GUOJ8Q")
        self.assertCalled("GET", "/retailer/orders/C000GUOJ8Q")
        self.assertIsInstance(order, Order)
        self.assertEqual(order.orderItems[0].orderItemId, "9203065392")

    def test_ship_order_item_posts_to_the_shipments_group(self):
        api = self.api_for_fixture("bol/process_status_submitted_shipment.json")
        status = api.orders.ship_order_item("9203065392", "SHIP-1")
        self.assertCalled("POST", "/retailer/shipments")
        self.assertJson(
            {
                "orderItems": [{"orderItemId": "9203065392"}],
                "shipmentReference": "SHIP-1",
            }
        )
        self.assertIsInstance(status, ProcessStatus)
        self.assertEqual(status.status, "PENDING")

    def test_ship_order_item_with_a_transporter_and_quantity(self):
        api = self.api_for_fixture("bol/process_status_submitted_shipment.json")
        api.orders.ship_order_item(
            "9203065392",
            "SHIP-1",
            transporter_code="TNT",
            track_and_trace="3STOTA123",
            quantity=2,
        )
        self.assertJson(
            {
                "orderItems": [{"orderItemId": "9203065392", "quantity": 2}],
                "shipmentReference": "SHIP-1",
                "transport": {
                    "transporterCode": "TNT",
                    "trackAndTrace": "3STOTA123",
                },
            }
        )

    def test_ship_order_item_with_a_label_id_sends_no_transport(self):
        api = self.api_for_fixture("bol/process_status_submitted_shipment.json")
        api.orders.ship_order_item(
            "9203065392",
            "SHIP-1",
            shipping_label_id="label-1",
            transporter_code="TNT",
        )
        body = self.session.json()
        self.assertEqual(body["shippingLabelId"], "label-1")
        self.assertNotIn("transport", body)

    def test_cancel_order_item(self):
        api = self.api_for_fixture("bol/process_status_submitted_shipment.json")
        status = api.orders.cancel_order_item(
            "9203065392", "REQUESTED_BY_CUSTOMER"
        )
        self.assertCalled("PUT", "/retailer/orders/cancellation")
        self.assertJson(
            {
                "orderItems": [
                    {
                        "orderItemId": "9203065392",
                        "reasonCode": "REQUESTED_BY_CUSTOMER",
                    }
                ]
            }
        )
        self.assertIsInstance(status, ProcessStatus)


class TestOrdersDemo(TestOrders):
    """The demo environment is a URL prefix, and every call must carry it."""

    demo = True

    def assertCalled(self, method, path, index=0):
        call = self.session.call(index)
        self.assertEqual(call["method"], method)
        self.assertEqual(
            call["url"],
            "https://api.bol.com" + path.replace("/retailer/", "/retailer-demo/", 1),
        )


class TestOffers(CallSiteCase):
    """The densest group: six writes, one receipt shape, one CSV export."""

    def test_get_single_offer(self):
        api = self.api_for_fixture("synthetic/offer_single.json")
        offer = api.offers.getSingleOffer("13722de8-8182-d161-5422-4a0a1caab5c8")
        self.assertCalled(
            "GET", "/retailer/offers/13722de8-8182-d161-5422-4a0a1caab5c8"
        )
        self.assertIsInstance(offer, OffersResponse)
        self.assertEqual(offer.stock.amount, 5)
        self.assertEqual(offer.fulfilment.method, "FBR")

    def test_create_single_offer(self):
        api = self.api_for_fixture("bol/process_status_submitted_export.json")
        data = {
            "ean": "8720849300131",
            "condition": {"name": "NEW"},
            "pricing": {"bundlePrices": [{"quantity": 1, "unitPrice": 12.95}]},
            "stock": {"amount": 5, "managedByRetailer": True},
            "fulfilment": {"method": "FBR"},
        }
        status = api.offers.createSingleOffer(data)
        self.assertCalled("POST", "/retailer/offers")
        self.assertJson(data)
        self.assertIsInstance(status, ProcessStatus)

    def test_update_product(self):
        api = self.api_for_fixture("bol/process_status_submitted_export.json")
        data = {"fulfilment": {"method": "FBR"}, "referenceCode": "REF-1"}
        api.offers.updateProduct("offer-1", data)
        self.assertCalled("PUT", "/retailer/offers/offer-1")
        self.assertJson(data)

    def test_update_product_price(self):
        api = self.api_for_fixture("bol/process_status_submitted_export.json")
        data = {"pricing": {"bundlePrices": [{"quantity": 1, "unitPrice": 9.5}]}}
        api.offers.updateProductPrice("offer-1", data)
        self.assertCalled("PUT", "/retailer/offers/offer-1/price")
        self.assertJson(data)

    def test_update_product_stock(self):
        api = self.api_for_fixture("bol/process_status_submitted_export.json")
        data = {"amount": 3, "managedByRetailer": True}
        api.offers.updateProductStock("offer-1", data)
        self.assertCalled("PUT", "/retailer/offers/offer-1/stock")
        self.assertJson(data)

    def test_delete_offers(self):
        api = self.api_for_fixture("bol/process_status_submitted_export.json")
        api.offers.deleteOffers("offer-1")
        self.assertCalled("DELETE", "/retailer/offers/offer-1")

    def test_request_export_file(self):
        api = self.api_for_fixture("bol/process_status_submitted_export.json")
        status = api.offers.requestExportFile()
        self.assertCalled("POST", "/retailer/offers/export")
        self.assertJson({"format": "CSV"})
        self.assertEqual(status.eventType, "CREATE_OFFER_EXPORT")

    def test_every_write_carries_the_json_content_type(self):
        api = self.api_for_fixture("bol/process_status_submitted_export.json")
        api.offers.updateProductStock("offer-1", {"amount": 1})
        self.assertEqual(
            self.session.headers_sent()["content-type"],
            "application/vnd.retailer.v10+json",
        )


class TestProcessStatus(CallSiteCase):
    """The poller. ``shared``, not ``retailer`` — the only group whose base differs."""

    def test_get_by_id(self):
        api = self.api_for_fixture("bol/process_status_submitted_export.json")
        status = api.process_status.getById("01a0453c-0303-73cd-9b90-d84c8e1babe9")
        self.assertCalled(
            "GET", "/shared/process-status/01a0453c-0303-73cd-9b90-d84c8e1babe9"
        )
        self.assertIsInstance(status, ProcessStatus)

    def test_get_by_ids(self):
        api = self.api_for_fixture("bol/process_status_getbyids_success.json")
        statuses = api.process_status.getByIds(["one", "two"])
        self.assertCalled("POST", "/shared/process-status")
        self.assertJson(
            {
                "processStatusQueries": [
                    {"processStatusId": "one"},
                    {"processStatusId": "two"},
                ]
            }
        )
        self.assertIsInstance(statuses, ProcessStatuses)
        self.assertEqual(statuses[0].status, "SUCCESS")
        self.assertEqual(
            statuses[0].entityId, "5e09af3a-3c35-487a-a477-c3c41f23180d"
        )

    def test_get_by_ids_reads_a_terminal_failure(self):
        api = self.api_for_fixture("bol/process_status_getbyids_failure.json")
        statuses = api.process_status.getByIds(["one"])
        self.assertEqual(statuses[0].status, "FAILURE")
        self.assertTrue(statuses[0].errorMessage)

    def test_get_by_ids_reads_one_still_pending(self):
        api = self.api_for_fixture(
            "bol/process_status_getbyids_export_pending.json"
        )
        statuses = api.process_status.getByIds(["one"])
        self.assertEqual(statuses[0].status, "PENDING")

    def test_get_by_entity(self):
        api = self.api_for_fixture("bol/process_status_getbyids_success.json")
        api.process_status.get("entity-1", "CREATE_SHIPMENT", page=2)
        self.assertCalled("GET", "/shared/process-status")
        self.assertParams(
            {"entity-id": "entity-1", "event-type": "CREATE_SHIPMENT", "page": 2}
        )


class TestReturns(CallSiteCase):
    def test_get(self):
        api = self.api_for_fixture("bol/returns_list.json")
        returns = api.returns.get()
        self.assertCalled("GET", "/retailer/returns")
        self.assertParams({"handled": False, "fulfilment-method": "FBR"})
        self.assertIsInstance(returns, ReturnItems)
        self.assertEqual(returns[0].returnId, "998810696")

    def test_get_page_two(self):
        api = self.api_for_fixture("bol/returns_list.json")
        api.returns.get(page=2, handled=True, fulfilment_method="FBB")
        self.assertParams(
            {"handled": True, "fulfilment-method": "FBB", "page": 2}
        )

    def test_get_single(self):
        api = self.api_for_fixture("synthetic/return_single.json")
        item = api.returns.getSingle("998810696")
        self.assertCalled("GET", "/retailer/returns/998810696")
        self.assertIsInstance(item, SingleReturnItem)
        self.assertEqual(item.returnItems[0].rmaId, "964219742")

    def test_handle_return_item(self):
        api = self.api_for_fixture("bol/process_status_submitted_shipment.json")
        status = api.returns.handleReturnItem("964219742", "RETURN_RECEIVED", 1)
        self.assertCalled("PUT", "/retailer/returns/964219742")
        self.assertJson(
            {"handlingResult": "RETURN_RECEIVED", "quantityReturned": 1}
        )
        self.assertIsInstance(status, ProcessStatus)


class TestEconomicOperators(CallSiteCase):
    """The media-type exception: a per-call Accept, not a session-wide one."""

    def test_list(self):
        api = self.api_for_fixture("bol/economic_operators.json")
        operators = api.economic_operators.list()
        self.assertCalled("GET", "/retailer/economic-operators")
        self.assertEqual(
            self.session.headers_sent()["Accept"],
            "application/vnd.economic-operator.v1+json",
        )
        self.assertIsInstance(operators, EconomicOperators)
        self.assertTrue(len(operators) > 0)

    def test_the_per_call_media_type_does_not_stick_to_the_session(self):
        api = self.api_for(
            response_from_fixture("bol/economic_operators.json"),
            response_from_fixture("bol/orders_page_1.json"),
        )
        api.set_access_token("token")
        api.economic_operators.list()
        api.orders.list()
        self.assertEqual(self.session.headers_sent(1), {})
        self.assertEqual(
            self.session.headers["Accept"], "application/vnd.retailer.v10+json"
        )


# ---------------------------------------------------------------------------
# The five raw-Response readers
# ---------------------------------------------------------------------------


class TestRawResponseReaders(CallSiteCase):
    """These five hand the response back so the caller can read bytes.

    ``getOffersFile`` returns CSV and the four label methods return PDF.
    Parsing any of them as JSON would raise, and the mistake would only show up
    when somebody exported an offer file or printed a label.
    """

    PDF = "%PDF-1.4 synthetic label bytes"
    CSV = "ean,offerId,stock\n8720849300131,offer-1,5\n"

    def test_get_offers_file_returns_the_response(self):
        api = self.api_for(
            make_response(
                raw_body=self.CSV,
                headers={"content-type": "application/vnd.retailer.v10+csv"},
            )
        )
        response = api.offers.getOffersFile("export-1")
        self.assertCalled("GET", "/retailer/offers/export/export-1")
        self.assertEqual(
            self.session.headers_sent()["accept"],
            "application/vnd.retailer.v10+csv",
        )
        self.assertEqual(response.text, self.CSV)
        self.assertEqual(response.status_code, 200)

    def test_get_shipping_label_returns_the_response(self):
        api = self.api_for(make_response(raw_body=self.PDF))
        response = api.labels.getShippingLabel("label-1")
        self.assertCalled("GET", "/retailer/shipping-labels/label-1")
        self.assertEqual(
            self.session.headers_sent()["accept"],
            "application/vnd.retailer.v10+pdf",
        )
        self.assertEqual(response.content, self.PDF.encode("utf-8"))

    def test_get_product_labels_returns_the_response(self):
        api = self.api_for(make_response(raw_body=self.PDF))
        response = api.replenishments.getProductLabels(
            "AVERY_J8159", [{"ean": "8720849300131", "quantity": 2}]
        )
        self.assertCalled("POST", "/retailer/replenishments/product-labels")
        self.assertJson(
            {
                "labelFormat": "AVERY_J8159",
                "products": [{"ean": "8720849300131", "quantity": 2}],
            }
        )
        self.assertEqual(response.content, self.PDF.encode("utf-8"))

    def test_get_load_carrier_labels_returns_the_response(self):
        api = self.api_for(make_response(raw_body=self.PDF))
        response = api.replenishments.getLoadCarrierLabels("repl-1")
        self.assertCalled(
            "GET", "/retailer/replenishments/repl-1/load-carrier-labels"
        )
        self.assertEqual(response.content, self.PDF.encode("utf-8"))

    def test_get_pick_list_returns_the_response(self):
        api = self.api_for(make_response(raw_body=self.PDF))
        response = api.replenishments.getPickList("repl-1")
        self.assertCalled("GET", "/retailer/replenishments/repl-1/pick-list")
        self.assertEqual(response.content, self.PDF.encode("utf-8"))

    def test_none_of_them_touches_response_json(self):
        # A CSV or PDF body is not JSON; if any of these ever started parsing,
        # this is the failure it would produce.
        api = self.api_for(make_response(raw_body=self.CSV))
        response = api.offers.getOffersFile("export-1")
        self.assertRaises(ValueError, response.json)


# ---------------------------------------------------------------------------
# Out of scope but must keep working: dbt_bol_fbb and dbt_bol_vvb, 13 sites
# ---------------------------------------------------------------------------


class TestFbbCallSites(CallSiteCase):
    """``dbt_bol_fbb`` is not edited by this package, so it must not need to be."""

    def test_orders_list_fbb(self):
        api = self.api_for_fixture("bol/orders_page_1.json")
        api.orders.list(fulfilment_method="FBB", status="ALL")
        self.assertCalled("GET", "/retailer/orders")
        self.assertParams({"fulfilment-method": "FBB", "status": "ALL"})

    def test_inventory_get_with_no_arguments(self):
        api = self.api_for_fixture("bol/inventory_page_1.json")
        inventory = api.inventory.get()
        self.assertCalled("GET", "/retailer/inventory")
        self.assertParams({})
        self.assertIsInstance(inventory, Inventories)

    def test_inventory_get_with_a_page(self):
        api = self.api_for_fixture("bol/inventory_page_1.json")
        api.inventory.get({"page": 3})
        self.assertParams({"page": 3})

    def test_inventory_get_does_not_share_a_default_dict_between_calls(self):
        """B006. The default used to be a literal ``{}`` shared by every call."""
        api = self.api_for(
            response_from_fixture("bol/inventory_page_1.json"),
            response_from_fixture("bol/inventory_page_1.json"),
        )
        api.inventory.get({"page": 2})
        api.inventory.get()
        self.assertParams({"page": 2}, index=0)
        self.assertParams({}, index=1)

    def test_replenishments_get(self):
        api = self.api_for_body({"replenishments": []})
        result = api.replenishments.get(state="Announced")
        self.assertCalled("GET", "/retailer/replenishments")
        self.assertParams({"state": "Announced"})
        self.assertIsInstance(result, Replenishments)

    def test_replenishments_create(self):
        api = self.api_for_fixture("bol/process_status_submitted_export.json")
        payload = {"reference": "REPL-1", "lines": []}
        api.replenishments.create(payload)
        self.assertCalled("POST", "/retailer/replenishments")
        self.assertJson(payload)

    def test_replenishments_get_by_id(self):
        api = self.api_for_body({"replenishmentId": "repl-1"})
        result = api.replenishments.getById("repl-1")
        self.assertCalled("GET", "/retailer/replenishments/repl-1")
        self.assertIsInstance(result, Replenishment)

    def test_replenishments_update(self):
        api = self.api_for_fixture("bol/process_status_submitted_export.json")
        api.replenishments.update("repl-1", state="Cancelled")
        self.assertCalled("PUT", "/retailer/replenishments/repl-1")
        self.assertJson({"state": "Cancelled"})

    def test_replenishments_pickup_time_slots(self):
        api = self.api_for_body({"timeSlots": []})
        result = api.replenishments.getpickupTimeSlots(
            {"countryCode": "NL"}, 2
        )
        self.assertCalled("POST", "/retailer/replenishments/pickup-time-slots")
        self.assertJson({"address": {"countryCode": "NL"}, "numberOfLoadCarriers": 2})
        self.assertIsInstance(result, TimeSlots)


class TestVvbCallSites(CallSiteCase):
    """``dbt_bol_vvb`` is not edited by this package either."""

    def test_get_delivery_options(self):
        api = self.api_for_fixture("synthetic/delivery_options.json")
        options = api.labels.getDeliveryOptions(
            [{"orderItemId": "9203065392", "quantity": 1}]
        )
        self.assertCalled("POST", "/retailer/shipping-labels/delivery-options")
        self.assertJson(
            {"orderItems": [{"orderItemId": "9203065392", "quantity": 1}]}
        )
        self.assertIsInstance(options, ShippingLabels)
        self.assertEqual(options[0].labelPrice.totalPrice, Decimal("5.75"))

    def test_create_shipping_label(self):
        api = self.api_for_fixture("bol/process_status_submitted_shipment.json")
        status = api.labels.createShippingLabel(
            [{"orderItemId": "9203065392"}], "label-offer-1"
        )
        self.assertCalled("POST", "/retailer/shipping-labels")
        self.assertJson(
            {
                "orderItems": [{"orderItemId": "9203065392"}],
                "shippingLabelOfferId": "label-offer-1",
            }
        )
        self.assertIsInstance(status, ProcessStatus)


class TestModelCoercionSurvivedTheMove(CallSiteCase):
    """The ``Meta``-coercion layer is out of scope and must be untouched by it."""

    def test_decimals_stay_decimals(self):
        api = self.api_for_fixture("synthetic/offer_single.json")
        offer = api.offers.getSingleOffer("offer-1")
        self.assertIsInstance(
            offer.pricing.bundlePrices[0].unitPrice, Decimal
        )

    def test_datetimes_are_parsed(self):
        api = self.api_for_fixture("bol/orders_page_1.json")
        orders = api.orders.list()
        self.assertEqual(orders[0].orderPlacedDateTime.year, 2026)

    def test_unknown_keys_pass_through_raw(self):
        api = self.api_for_body({"orderId": "X", "somethingBolAddedToday": 42})
        order = api.orders.get("X")
        self.assertEqual(order.somethingBolAddedToday, 42)

    def test_the_raw_payload_is_kept(self):
        api = self.api_for_fixture("bol/orders_page_1.json")
        orders = api.orders.list()
        self.assertIn("orders", orders.raw_data)


class TestOfferModelStillImportable(unittest.TestCase):
    """A smoke check that the models module was not disturbed."""

    def test_offer_parses(self):
        offer = Offer.parse(None, '{"offerId": "x"}')
        self.assertEqual(offer.offerId, "x")


if __name__ == "__main__":
    unittest.main()
