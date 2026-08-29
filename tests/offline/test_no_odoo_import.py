"""The dependency runs one way, and this is the test that keeps it that way.

``python-bol-api-latest`` is a public package. The Odoo connector that injects
a transport into it depends on *it*; it must never depend on the connector, on
``dbt_base_connector`` or on Odoo. If it did, installing it from PyPI would ask
a stranger to install an ERP.

Modelled on the platform's own ``transport/tests/test_no_odoo_import.py``,
which asserts the same constraint from the other side of the boundary. If this
test ever fails, the fix is to move the offending code out of the library, not
to relax the test.
"""

import ast
import os
import re
import sys
import unittest

PACKAGE_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "bol",
)
TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))

#: Third-party imports the library is allowed to make. Both are declared in
#: setup.py's install_requires; nothing else may appear.
ALLOWED_THIRD_PARTY = {"requests", "dateutil"}

#: ``urlparse`` is the Python 2 spelling of ``urllib.parse`` and is reached
#: only through an ImportError fallback. It is stdlib where it exists.
STDLIB_ALIASES = {"urlparse"}

#: Import roots that would mean the dependency has been inverted.
FORBIDDEN = ("odoo", "dbt_base_connector", "dbt_bol_connector", "odoo_addons")

#: Built rather than written out so that this file passes its own check.
ENV_SUFFIX = os.extsep + "env"

#: A dynamic import, which the AST check cannot see.
DYNAMIC_IMPORT = re.compile(
    r"""(?:__import__|import_module)\s*\(\s*["'](?:odoo|dbt_)"""
)


def python_files(root):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in sorted(filenames):
            if name.endswith(".py"):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def read(path):
    with open(path, "rb") as handle:
        return handle.read().decode("utf-8")


def imported_roots(tree):
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import, inside this package
                continue
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


class TestNoConnectorImport(unittest.TestCase):
    def test_there_are_files_to_check(self):
        self.assertGreater(len(python_files(PACKAGE_ROOT)), 3)

    def test_no_library_module_imports_odoo_or_the_connector(self):
        offenders = []
        for path in python_files(PACKAGE_ROOT):
            tree = ast.parse(read(path), filename=path)
            for root in imported_roots(tree):
                if root in FORBIDDEN:
                    offenders.append((os.path.basename(path), root))
        self.assertEqual(
            offenders,
            [],
            "a public PyPI package cannot depend on an Odoo addon: %s"
            % (offenders,),
        )

    def test_no_library_module_imports_them_dynamically(self):
        offenders = [
            os.path.basename(path)
            for path in python_files(PACKAGE_ROOT)
            if DYNAMIC_IMPORT.search(read(path))
        ]
        self.assertEqual(offenders, [])

    def test_third_party_imports_stay_on_the_short_list(self):
        stdlib = set(getattr(sys, "stdlib_module_names", ())) | STDLIB_ALIASES
        unexpected = {}
        for path in python_files(PACKAGE_ROOT):
            tree = ast.parse(read(path), filename=path)
            for root in imported_roots(tree):
                if root in stdlib or root in ALLOWED_THIRD_PARTY:
                    continue
                if root == "bol":  # the package importing itself absolutely
                    continue
                unexpected.setdefault(root, []).append(os.path.basename(path))
        self.assertEqual(unexpected, {})

    def test_the_transport_module_imports_only_requests(self):
        """The seam itself is the module most likely to grow a dependency."""
        path = os.path.join(PACKAGE_ROOT, "retailer", "transport.py")
        tree = ast.parse(read(path), filename=path)
        stdlib = set(getattr(sys, "stdlib_module_names", ())) | STDLIB_ALIASES
        for root in imported_roots(tree):
            self.assertTrue(
                root in stdlib or root == "requests",
                "bol/retailer/transport.py must import nothing but the "
                "standard library and requests; found %r" % root,
            )


class TestTheOfflineSuiteIsSelfContained(unittest.TestCase):
    """The tests must run from a fresh clone with nothing else installed."""

    def test_the_offline_tests_import_nothing_of_the_connector_s(self):
        offenders = []
        for path in python_files(TESTS_ROOT):
            tree = ast.parse(read(path), filename=path)
            for root in imported_roots(tree):
                if root in FORBIDDEN:
                    offenders.append((os.path.basename(path), root))
        self.assertEqual(offenders, [])

    def test_the_offline_tests_need_no_credentials(self):
        """No ``dotenv``, no ``.env`` file, no client id, no client secret.

        The suite this one replaces logs in to bol.com in ``setUp`` and carries
        a live client id and secret as a literal fallback. Nothing here may.
        Checked against the syntax tree rather than the text, so that prose
        about credentials does not trip it and an assignment cannot hide.
        """
        for path in python_files(TESTS_ROOT):
            tree = ast.parse(read(path), filename=path)
            name = os.path.basename(path)
            self.assertNotIn("dotenv", imported_roots(tree), name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    self.assertNotIn(
                        node.id.upper(),
                        ("CLIENT_ID", "CLIENT_SECRET"),
                        "%s must not carry credentials" % name,
                    )
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    self.assertFalse(
                        node.value.endswith(ENV_SUFFIX),
                        "%s must not read an .env file" % name,
                    )

    #: Calling any of these on ``requests`` puts a packet on the wire.
    #: ``requests.Session`` and ``requests.Response`` are absent on purpose:
    #: naming a type is fine, and both are named in assertions here.
    NETWORK_FUNCTIONS = frozenset(
        ["get", "post", "put", "delete", "head", "patch", "request"]
    )

    def test_the_offline_tests_open_no_sockets(self):
        """``requests`` is used for its types, never for its transport."""
        for path in python_files(TESTS_ROOT):
            tree = ast.parse(read(path), filename=path)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute):
                    continue
                if isinstance(func.value, ast.Name) and func.value.id == "requests":
                    self.assertNotIn(
                        func.attr,
                        self.NETWORK_FUNCTIONS,
                        "%s calls requests.%s()"
                        % (os.path.basename(path), func.attr),
                    )


if __name__ == "__main__":
    unittest.main()
