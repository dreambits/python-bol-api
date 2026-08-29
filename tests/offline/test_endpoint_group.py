"""The endpoint grouping, which a rate limiter cannot get right on its own.

bol.com publishes a live budget on every response — ``x-ratelimit-limit`` /
``-remaining`` / ``-reset`` — and the budget is **per resource group**, with
genuinely different numbers: 25 for orders, 20 for returns, 20 for inventory,
100 for economic-operators, 2 for process-status.

A limiter that groups on the first path segment — the obvious rule, and the
default of the one this library is used with — sees ``/retailer/orders`` and
``/retailer/economic-operators`` and calls both ``retailer``. That is wrong in
the dangerous direction: economic-operators reporting ``remaining: 99``
overwrites orders reporting ``remaining: 3`` under the shared key, so the
limiter believes it has budget it does not have and spends straight into 429s.
Every test still passes while it happens, which is why this file exists.

The library is the only place that knows the answer, because the library is
what builds the URL.
"""

import unittest

import bol.retailer.api as api_module
from bol.retailer.api import MethodGroup, RetailerAPI
from bol.retailer.transport import BASE_TYPES, build_uri, endpoint_group

from .support import StubSession, make_response

#: The five in-scope base paths, and the five distinct groups they must map to.
IN_SCOPE_PATHS = {
    "/retailer/orders": "orders",
    "/retailer/offers": "offers",
    "/retailer/returns": "returns",
    "/retailer/economic-operators": "economic-operators",
    "/shared/process-status": "process-status",
}


class TestFiveDistinctGroups(unittest.TestCase):
    """Acceptance 3. Without this the rate limiter is silently wrong."""

    def test_each_in_scope_path_maps_to_its_own_group(self):
        for path, group in sorted(IN_SCOPE_PATHS.items()):
            self.assertEqual(endpoint_group(path), group, path)

    def test_the_five_groups_are_five_and_not_one(self):
        groups = {endpoint_group(path) for path in IN_SCOPE_PATHS}
        self.assertEqual(len(groups), 5, sorted(groups))
        self.assertNotIn("retailer", groups)
        self.assertNotIn("shared", groups)

    def test_the_naive_first_segment_rule_really_would_collapse_them(self):
        # Guards the premise: if this ever stops being true the grouping
        # function is solving a problem that no longer exists.
        first_segments = {
            path.strip("/").split("/")[0] for path in IN_SCOPE_PATHS
        }
        self.assertEqual(first_segments, {"retailer", "shared"})


class TestDerivedFromTheSameRule(unittest.TestCase):
    """One definition, not two: ``endpoint_group`` is ``build_uri`` backwards."""

    def test_method_group_builds_its_uri_with_build_uri_and_nothing_else(self):
        """If this fails there are two copies of the rule, and they will drift."""
        calls = []

        def spy(base_type, group, path="", demo=False):
            calls.append((base_type, group, path, demo))
            return build_uri(base_type, group, path, demo=demo)

        session = StubSession(responses=[make_response(body={})])
        api = RetailerAPI(demo=True, session=session)
        original = api_module.build_uri
        api_module.build_uri = spy
        try:
            api.orders.get("C000GUOJ8Q")
        finally:
            api_module.build_uri = original

        self.assertEqual(calls, [("retailer", "orders", "C000GUOJ8Q", True)])
        self.assertEqual(
            session.url(), "https://api.bol.com/retailer-demo/orders/C000GUOJ8Q"
        )

    def test_every_method_group_on_the_api_round_trips(self):
        for demo in (False, True):
            api = RetailerAPI(demo=demo)
            groups = [
                member
                for member in vars(api).values()
                if isinstance(member, MethodGroup)
            ]
            self.assertEqual(len(groups), 13)
            for group in groups:
                uri = build_uri(
                    group.base_type, group.group, "", demo=api.demo
                )
                self.assertEqual(
                    endpoint_group(uri),
                    group.group,
                    "%s -> %s" % (uri, group.group),
                )

    def test_every_base_type_the_library_uses_is_known_to_the_grouping(self):
        # This is what keeps BASE_TYPES honest without the method groups
        # having to import it.
        api = RetailerAPI()
        for member in vars(api).values():
            if isinstance(member, MethodGroup):
                self.assertIn(member.base_type, BASE_TYPES, member.group)

    def test_a_path_below_the_group_still_groups_with_it(self):
        self.assertEqual(endpoint_group("/retailer/orders/C000GUOJ8Q"), "orders")
        self.assertEqual(
            endpoint_group("/retailer/offers/13722de8/stock"), "offers"
        )
        self.assertEqual(
            endpoint_group("/shared/process-status/01a04540"), "process-status"
        )

    def test_demo_is_the_same_group_as_live(self):
        self.assertEqual(endpoint_group("/retailer-demo/orders"), "orders")
        self.assertEqual(
            endpoint_group("/shared-demo/process-status"), "process-status"
        )

    def test_an_override_group_is_the_group_that_counts(self):
        # orders.ship_order_item POSTs to /retailer/shipments, which has its
        # own budget and must not be counted against orders'.
        uri = build_uri("retailer", "shipments", "")
        self.assertEqual(endpoint_group(uri), "shipments")


class TestAcceptsUrlsAndPaths(unittest.TestCase):
    """A limiter sees the path on the way out and the URL on the way back."""

    def test_a_whole_url_reduces_to_the_same_group(self):
        self.assertEqual(
            endpoint_group("https://api.bol.com/retailer/orders?page=2"),
            endpoint_group("/retailer/orders"),
        )

    def test_a_url_with_a_fragment_and_query_is_handled(self):
        self.assertEqual(
            endpoint_group(
                "https://api.bol.com/retailer/returns?handled=false#x"
            ),
            "returns",
        )

    def test_a_bare_path_without_a_base_prefix_falls_back_to_its_segment(self):
        # For a caller whose base_url already carries /retailer.
        self.assertEqual(endpoint_group("/orders"), "orders")
        self.assertEqual(endpoint_group("orders/C000GUOJ8Q"), "orders")

    def test_the_auth_host_is_not_an_api_group(self):
        # login.bol.com publishes no quota headers; grouping it is harmless
        # but it must not land in a resource group's bucket.
        self.assertEqual(endpoint_group("https://login.bol.com/token"), "token")

    def test_degenerate_input_does_not_raise(self):
        for value in ("", "/", None, "https://api.bol.com", "https://api.bol.com/"):
            self.assertEqual(endpoint_group(value), "")


class TestBuildUri(unittest.TestCase):
    def test_builds_the_documented_shape(self):
        self.assertEqual(build_uri("retailer", "orders"), "/retailer/orders")
        self.assertEqual(
            build_uri("retailer", "orders", "C000GUOJ8Q"),
            "/retailer/orders/C000GUOJ8Q",
        )

    def test_demo_suffixes_the_base_and_not_the_group(self):
        self.assertEqual(
            build_uri("retailer", "orders", demo=True), "/retailer-demo/orders"
        )
        self.assertEqual(
            build_uri("shared", "process-status", demo=True),
            "/shared-demo/process-status",
        )

    def test_an_empty_path_adds_no_trailing_slash(self):
        self.assertEqual(build_uri("retailer", "offers", ""), "/retailer/offers")


if __name__ == "__main__":
    unittest.main()
