==============
python-bol-api
==============

.. image:: https://app.travis-ci.com/dreambits/python-bol-api.svg?branch=master
    :target: https://app.travis-ci.com/dreambits/python-bol-api

.. image:: https://badge.fury.io/py/python-bol-api.png
   :target: http://badge.fury.io/py/python-bol-api

.. image:: https://badge.fury.io/py/python-bol-api-latest.svg
    :target: https://badge.fury.io/py/python-bol-api-latest

.. image:: https://codecov.io/gh/dreambits/python-bol-api/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/dreambits/python-bol-api

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

Plaza API
=========

Plaza API is removed in the latest release v1.0 as it is now not supported by Bol.com

Retailer API
============

Supports the BOL API V5, documented here: https://api.bol.com/retailer/public/Retailer-API/selling-on-bolcom-processflow.html

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

    >>> repr(order.dateTimeOrderPlace)
    datetime.datetime(2020, 2, 12, 16, 6, 17, tzinfo=tzoffset(None, 3600))
    >>> repr(order.orderItems[0].offerPrice)
    Decimal('106.52')

Access the underlying raw (unparsed) data at any time::

    >>> order.raw_data
    >>> order.raw_content


Running the tests
=================

First, make sure that you have ``tox`` installed on your system::

    pip install tox

Then, just run the tox::

    tox
