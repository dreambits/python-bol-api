==============
python-bol-api
==============

.. image:: https://app.travis-ci.com/dreambits/python-bol-api.svg?branch=master
    :target: https://app.travis-ci.com/dreambits/python-bol-api

.. image:: https://badge.fury.io/py/python-bol-api-latest.svg
    :target: https://badge.fury.io/py/python-bol-api-latest

.. image:: https://static.pepy.tech/personalized-badge/python-bol-api-latest?period=total&units=international_system&left_color=brightgreen&right_color=black&left_text=Downloads
 :target: https://pepy.tech/project/python-bol-api-latest

A Python wrapper for the bol.com API forked from https://github.com/pennersr/python-bol-api
This is currently under development but stable to be used.
We are adding more and more features as the api has changed a lot from the time this version was created in original project

A Python wrapper for the bol.com API. Currently rather incomplete, as
it offers only those methods required for my own projects so far.


Open API
========

Instantiate the API::

    >>> from bol.openapi.api import OpenAPI
    >>> api = OpenAPI('api_key')

Invoke a method::

    >>> data = api.catalog.products((['1004004011187773', '1004004011231766'])

JSON data is returned "as is":

    >>> data['products'][0]['ean']
    u'0093155141650'

Retailer API
============

Supports the BOL Api v10, documented here: https://api.bol.com/retailer/public/Retailer-API/selling-on-bolcom-processflow.html

Instantiate the API::

    >>> from bol.retailer.api import RetailerAPI
    >>> api = RetailerAPI()

Authenticate::

    >>> api.login('client_id', 'client_secret')

Invoke a method::

    >>> orders = api.orders.list()
    >>> order = api.orders.get(orders[0].orderId))

Fields are derived 1:1 from the bol.com API, including lower-CamelCase
conventions::

    >>> order.customerDetails.shipmentDetails.streetName
    'Billingstraat'

Fields are properly typed::

    >>> repr(order.orderPlacedDateTime)
    datetime.datetime(2020, 2, 12, 16, 6, 17, tzinfo=tzoffset(None, 3600))
    >>> repr(order.orderItems[0].offerPrice)
    Decimal('106.52')

Access the underlying raw (unparsed) data at any time::

    >>> order.raw_data
    >>> order.raw_content


Supplying your own transport
============================

*New in 1.6.0, and entirely optional.* By default ``RetailerAPI`` performs its
HTTP with a ``requests.Session``, exactly as it always has. If you need
something more — timeouts, bounded retry, throttling against bol.com's
``x-ratelimit-*`` budget, typed errors, redacted logging — pass a ``transport``
and it will be used for every call, including ``login``::

    >>> api = RetailerAPI(transport=my_transport)

A transport is any object with four methods; it does not have to subclass
anything::

    class Transport:
        def request(self, method, url, params=None, json=None,
                    headers=None, timeout=None, **kwargs):
            """Perform one call and return the requests.Response."""

        def login(self, login_url, client_id, client_secret):
            """Return the parsed token document, containing access_token."""

        def set_access_token(self, access_token):
            """Use this token for subsequent requests."""

        def close(self):
            """Release any connection resources."""

``bol.retailer.transport.Transport`` documents it and
``bol.retailer.transport.RequestsTransport`` is the default implementation.

``request()`` must return the response object rather than a parsed body: five
methods — ``offers.getOffersFile`` and the four label downloads — hand it
straight back so the caller can read CSV or PDF bytes.

Two helpers come with it. ``bol.retailer.transport.build_uri`` is the
``/{base}/{group}{path}`` rule the library uses to address bol.com, and
``bol.retailer.transport.endpoint_group`` reads it backwards::

    >>> from bol.retailer.transport import endpoint_group
    >>> endpoint_group('/retailer/orders')
    'orders'
    >>> endpoint_group('/shared/process-status')
    'process-status'

That second one matters if you rate limit. bol.com publishes a **different**
budget per resource group — 25 for orders, 20 for returns, 100 for
economic-operators, 2 for process-status — and a limiter that keys on the first
path segment sees ``retailer`` for four of them and merges four budgets into
one. Use ``endpoint_group`` as your grouping function and they stay separate.


Running the tests
=================

The offline suite needs no account, no credentials and no network::

    python -m pytest tests/offline

For the full matrix, make sure that you have ``tox`` installed on your
system::

    pip install tox

Then, just run the tox::

    tox
