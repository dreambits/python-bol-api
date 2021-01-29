import pytest

from decimal import Decimal
from datetime import datetime
from dateutil.tz import tzoffset

from bol.retailer.api import RetailerAPI

from httmock import HTTMock, urlmatch

api = None
LOGIN_RESPONSE = """
{
    "access_token": "test_access_token",
    "token_type": "Bearer",
    "expires_in": 299,
    "scope": "scopes"
}
"""

ORDERS_RESPONSE = """
{
  "orders": [
    {
      "orderId": "A2K8290LP8",
      "orderPlacedDateTime": "2017-02-09T12:39:48+01:00",
      "orderItems": [
        {
          "orderItemId": "2012345678",
          "ean": "0000007740404",
          "quantity": 10
        },
        {
          "orderItemId": "2012345679",
          "ean": "0000007740407",
          "quantity": 1
        }
      ]
    }
  ]
}
"""

ORDERS_BY_ID_RESPONSE = """
{
  "orderId": "2K8290LP8",
  "pickUpPoint": true,
  "orderPlacedDateTime": "2017-02-09T12:39:48+01:00",
  "shipmentDetails": {
    "pickUpPointName": "Albert Heijn: UTRECHT",
    "salutation": "MALE",
    "firstName": "Billie",
    "surname": "Jansen",
    "streetName": "Dorpstraat",
    "houseNumber": "1",
    "houseNumberExtension": "B",
    "extraAddressInformation": "Apartment",
    "zipCode": "1111ZZ",
    "city": "Utrecht",
    "countryCode": "NL",
    "email": "billie@verkopen.bol.com",
    "company": "bol.com",
    "deliveryPhoneNumber": "012123456",
    "language": "nl"
  },
  "billingDetails": {
    "salutation": "MALE",
    "firstName": "Billie",
    "surname": "Jansen",
    "streetName": "Dorpstraat",
    "houseNumber": "1",
    "houseNumberExtension": "B",
    "extraAddressInformation": "Apartment",
    "zipCode": "1111ZZ",
    "city": "Utrecht",
    "countryCode": "NL",
    "email": "billie@verkopen.bol.com",
    "company": "bol.com",
    "vatNumber": "NL999999999B99",
    "kvkNumber": "99887766",
    "orderReference": "MijnReferentie"
  },
  "orderItems": [
    {
      "orderItemId": "2012345678",
      "cancellationRequest": false,
      "fulfilment": {
        "method": "FBR",
        "distributionParty": "RETAILER",
        "latestDeliveryDate": "2017-02-10",
        "exactDeliveryDate": "2017-02-13",
        "expiryDate": "2017-02-13"
      },
      "offer": {
        "offerId": "6ff736b5-cdd0-4150-8c67-78269ee986f5",
        "reference": "BOLCOM00123"
      },
      "product": {
        "ean": "0000007740404",
        "title": "Product Title"
      },
      "quantity": 10,
      "unitPrice": 12.99,
      "commission": 5.18,
      "additionalServices": [
        {
          "serviceType": "PLACEMENT_AND_INSTALLATION"
        }
      ]
    }
  ]
}
"""

SHIPMENTS_RESPONSE = """
"""

CREATE_SHIPMENT_RESPONSE = """
"""

UPDATE_TRANSPORT_RESPONSE = """
"""


@urlmatch(path=r'/token')
def login_stub(url, request):
    data = request.body
    print(data)
    # data_dic = data.split("&")
    # print(data_dic)
    # client_sec = data_dic[1]
    # if client_sec == "client_secret=api_secret":
    # print()
    # return {}
    return LOGIN_RESPONSE


@urlmatch(path=r'/services/rest/shipments/v2$')
def shipments_stub(url, request):
    return SHIPMENTS_RESPONSE


def test_login():
    with HTTMock(login_stub):
        api = RetailerAPI(demo=False)
        token = api.login('api_key', 'api_secret')
        assert token['access_token'] == "test_access_token"


def test_orders():
    with HTTMock(login_stub):
        api = RetailerAPI(demo=False)
        token = api.login('api_key', 'api_secret')
        assert token['access_token'] == "test_access_token"

        @urlmatch(path=r'/retailer/orders$')
        def orders_stub(url, request):
            return ORDERS_RESPONSE

        with HTTMock(orders_stub):
            orders = api.orders.list()
            print(orders)

            order = orders[0]
            assert order.orderId == "A2K8290LP8"

            item = order.orderItems[0]
            print(orders)
            # assert item.OrderItemId == '123'

# {
#   "orders": [
#     {
#       "orderId": "A2K8290LP8",
#       "orderPlacedDateTime": "2017-02-09T12:39:48+01:00",
#       "orderItems": [
#         {
#           "orderItemId": "2012345678",
#           "ean": "0000007740404",
#           "quantity": 10
#         }
#         {
#           "orderItemId": "2012345679",
#           "ean": "0000007740407",
#           "quantity": 1
#         }
#       ]
#     }
#   ]
# }

        @urlmatch(path=r'/retailer/orders')
        def order_by_id_stub(url, request):
            data = url.path
            print("DATA", url.path)
            data_dic = data.split("/")[-1]
            print(data_dic)

            if data_dic == "2K8290LP8":
                return ORDERS_BY_ID_RESPONSE
            return {}

        with HTTMock(order_by_id_stub):
            orById = api.orders.get('2K8290LP8')
            print(orById.orderId)

            assert orById.orderId == "2K8290LP8"
            assert isinstance(orById.pickUpPoint, bool)
            assert orById.pickUpPoint == True

            assert orById.orderPlacedDateTime == "2017-02-09T12:39:48+01:00"

            assert orById.shipmentDetails['pickUpPointName'] == "Albert Heijn: UTRECHT"
            assert orById.shipmentDetails['salutation'] == "MALE"
            assert orById.shipmentDetails['firstName'] == "Billie"
            assert orById.shipmentDetails['surname'] == "Jansen"
            assert orById.shipmentDetails['streetName'] == "Dorpstraat"
            assert orById.shipmentDetails['houseNumber'] == "1"
            assert orById.shipmentDetails['houseNumberExtension'] == "B"
            assert orById.shipmentDetails['extraAddressInformation'] == "Apartment"
            assert orById.shipmentDetails['zipCode'] == "1111ZZ"
            assert orById.shipmentDetails['city'] == "Utrecht"
            assert orById.shipmentDetails['countryCode'] == "NL"
            assert orById.shipmentDetails['email'] == "billie@verkopen.bol.com"
            assert orById.shipmentDetails['company'] == "bol.com"
            assert orById.shipmentDetails['deliveryPhoneNumber'] == "012123456"
            assert orById.shipmentDetails['language'] == "nl"

            assert orById.billingDetails["salutation"] == "MALE"
            assert orById.billingDetails["firstName"] == "Billie"
            assert orById.billingDetails["surname"] == "Jansen"
            assert orById.billingDetails["streetName"] == "Dorpstraat"
            assert orById.billingDetails["houseNumber"] == "1"
            assert orById.billingDetails["houseNumberExtension"] == "B"
            assert orById.billingDetails["extraAddressInformation"] == "Apartment"
            assert orById.billingDetails["zipCode"] == "1111ZZ"
            assert orById.billingDetails["city"] == "Utrecht"
            assert orById.billingDetails["countryCode"] == "NL"
            assert orById.billingDetails["email"] == "billie@verkopen.bol.com"
            assert orById.billingDetails["company"] == "bol.com"
            assert orById.billingDetails["vatNumber"] == "NL999999999B99"
            assert orById.billingDetails["kvkNumber"] == "99887766"
            assert orById.billingDetails["orderReference"] == "MijnReferentie"
            print(orById.billingDetails)
            item = orById.orderItems[0]
            assert item.orderItemId == "2012345678"
            isinstance(item.cancellationRequest, bool)

            assert item.cancellationRequest == False
            assert item.fulfilment["method"] == "FBR"
            assert item.fulfilment["distributionParty"] == "RETAILER"
            assert item.fulfilment["latestDeliveryDate"] == "2017-02-10"
            assert item.fulfilment["exactDeliveryDate"] == "2017-02-13"
            assert item.fulfilment["expiryDate"] == "2017-02-13"
            assert item.offer["offerId"] == "6ff736b5-cdd0-4150-8c67-78269ee986f5"
            assert item.offer["reference"] == "BOLCOM00123"
            assert item.product["ean"] == "0000007740404"
            assert item.product["title"] == "Product Title"
            assert isinstance(item.quantity, int)
            assert item.quantity == 10
            # assert isinstance(item.unitPrice, float)
            print("Unit price", item.unitPrice)
            assert item.unitPrice == Decimal('12.99')
            assert item.commission == Decimal('5.18')
            itemAdd = item.additionalServices[0]
            print(itemAdd)
            assert itemAdd["serviceType"] == "PLACEMENT_AND_INSTALLATION"
#   api.order.ship_order_item("123","ref","CODE1","TR1","TRACK_AND_TRACE")
