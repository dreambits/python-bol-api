import pytest
import json

from decimal import Decimal
from datetime import datetime
from dateutil.tz import tzoffset

from bol.retailer.api import RetailerAPI

from httmock import HTTMock, urlmatch

class Test_Retailer:
    api = RetailerAPI(demo=False)
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
    ORDER_CANCELLATION_RESPONSE = """
    {
    "id": 1234567,
    "entityId": "987654321",
    "eventType": "CONFIRM_SHIPMENT",
    "description": "Example process status description for processing 987654321.",
    "status": "SUCCESS",
    "errorMessage": "Example process status error message.",
    "createTimestamp": "2018-11-14T09:34:41+01:00",
    "links": [
        {
        "rel": "self",
        "href": "https://api.bol.com/retailer/process-status/1234567",
        "method": "GET"
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
    def login_stub(self, url, request):
        data = request.body
        print(data)
        # data_dic = data.split("&")
        # print(data_dic)
        # client_sec = data_dic[1]
        # if client_sec == "client_secret=api_secret":
        # print()
        # return {}
        return self.LOGIN_RESPONSE

    #multiple orders
    @urlmatch(path=r'/retailer/orders$') 
    def orders_stub(self, url, request):
        return self.ORDERS_RESPONSE
    
    #Order by orderId
    @urlmatch(path=r'/retailer/orders')
    def order_by_id_stub(self, url, request):
        data = url.path
        print("DATA", url.path)
        data_dic = data.split("/")[-1]
        print(data_dic)

        if data_dic == "2K8290LP8":
            return self.ORDERS_BY_ID_RESPONSE
        return {}

    #Order Cancellation
    @urlmatch(path=r'/retailer/orders/cancellation$')
    def orders_cancellation_stub(self, url, request):
        print("REquest Body" ,request.body)
        request_body = {
            "orderItems": [
                {
                "orderItemId": "2012345678",
                "reasonCode": "BAD_CONDITION"
                }
            ]
        }
        request_body = json.dumps(request_body).encode('utf-8')
        assert request.body == request_body #check the response
        return self.ORDER_CANCELLATION_RESPONSE


    @urlmatch(path=r'/services/rest/shipments/v2$')
    def shipments_stub(self, url, request):
        return self.SHIPMENTS_RESPONSE


    def test_login(self):
        with HTTMock(self.login_stub):
            api = RetailerAPI(demo=False)
            token = api.login('api_key', 'api_secret')
            assert token['access_token'] == "test_access_token"

    #multiple orders
    def test_all_orders(self):
        with HTTMock(self.orders_stub):
            orders = self.api.orders.list()
            print(orders)

            order = orders[0]
            print("Orders", order)
            assert order.orderId == "A2K8290LP8"
            assert order.orderPlacedDateTime == "2017-02-09T12:39:48+01:00"

            assert len(order.orderItems) == 2

            item1 = order.orderItems[0]
            assert item1.orderItemId == "2012345678"
            assert item1.ean == "0000007740404"
            assert item1.quantity == 10

            item2 = order.orderItems[1]
            assert item2.orderItemId == "2012345679"
            assert item2.ean == "0000007740407"
            assert item2.quantity == 1

    #Order by orderId
    def test_order_by_id(self): 
        with HTTMock(self.order_by_id_stub):
            orById = self.api.orders.get('2K8290LP8')
            print(orById.orderId)

            assert orById.orderId == "2K8290LP8"
            assert isinstance(orById.pickUpPoint, bool)
            assert orById.pickUpPoint == True

            assert orById.orderPlacedDateTime == "2017-02-09T12:39:48+01:00"

            assert orById.shipmentDetails.pickUpPointName == "Albert Heijn: UTRECHT"
            assert orById.shipmentDetails.salutation == "MALE"
            assert orById.shipmentDetails.firstName == "Billie"
            assert orById.shipmentDetails.surname == "Jansen"
            assert orById.shipmentDetails.streetName == "Dorpstraat"
            assert orById.shipmentDetails.houseNumber == "1"
            assert orById.shipmentDetails.houseNumberExtension == "B"
            assert orById.shipmentDetails.extraAddressInformation == "Apartment"
            assert orById.shipmentDetails.zipCode == "1111ZZ"
            assert orById.shipmentDetails.city == "Utrecht"
            assert orById.shipmentDetails.countryCode == "NL"
            assert orById.shipmentDetails.email == "billie@verkopen.bol.com"
            assert orById.shipmentDetails.company == "bol.com"
            assert orById.shipmentDetails.deliveryPhoneNumber == "012123456"
            assert orById.shipmentDetails.language == "nl"

            assert orById.billingDetails.salutation == "MALE"
            assert orById.billingDetails.firstName == "Billie"
            assert orById.billingDetails.surname == "Jansen"
            assert orById.billingDetails.streetName == "Dorpstraat"
            assert orById.billingDetails.houseNumber == "1"
            assert orById.billingDetails.houseNumberExtension == "B"
            assert orById.billingDetails.extraAddressInformation == "Apartment"
            assert orById.billingDetails.zipCode == "1111ZZ"
            assert orById.billingDetails.city == "Utrecht"
            assert orById.billingDetails.countryCode == "NL"
            assert orById.billingDetails.email == "billie@verkopen.bol.com"
            assert orById.billingDetails.company == "bol.com"
            assert orById.billingDetails.vatNumber == "NL999999999B99"
            assert orById.billingDetails.kvkNumber == "99887766"
            assert orById.billingDetails.orderReference == "MijnReferentie"
            print(orById.billingDetails)
            item = orById.orderItems[0]
            assert item.orderItemId == "2012345678"
            assert isinstance(item.cancellationRequest, bool)

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
    
    #Order by orderId
    def test_orders_cancellation(self): 
        with HTTMock(self.orders_cancellation_stub):
            cancle_order = self.api.orders.cancel_order_item(order_item_id = '2012345678', reason_code = "BAD_CONDITION")
            # print(dir(cancle_order))

            assert cancle_order.id == 1234567
            assert cancle_order.entityId == "987654321"
            assert cancle_order.eventType == "CONFIRM_SHIPMENT"
            assert cancle_order.description == "Example process status description for processing 987654321."
            assert cancle_order.status == "SUCCESS"
            assert cancle_order.errorMessage == "Example process status error message."
            # assert cancle_order.createTimestamp == datetime(
            # 2018, 9, 19, 18, 21, 59, 324000, tzinfo=tzoffset(None, 7200))"2018-11-14T09:34:41+01:00"
#   "links": [
#     {
#       "rel": "self",
#       "href": "https://api.bol.com/retailer/process-status/1234567",
#       "method": "GET"
#     }
#   ]
# }
    #   api.order.ship_order_item("123","ref","CODE1","TR1","TRACK_AND_TRACE")
