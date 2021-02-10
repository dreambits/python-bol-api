import pytest
import json

from decimal import Decimal
from datetime import datetime,date
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

    CREATE_NEW_OFFER_RESPONSE = """
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

    REQUEST_OFFER_EXPORT_FILE_RESPONSE = """
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

    RETRIEVE_OFFER_BY_OFFERID_RESPONSE = """
    {
    "offerId": "6ff736b5-cdd0-4150-8c67-78269ee986f5",
    "ean": "0000007740404",
    "reference": "REF12345",
    "onHoldByRetailer": false,
    "unknownProductTitle": "Unknown Product Title",
    "pricing": {
        "bundlePrices": [
        {
            "quantity": 1,
            "unitPrice": 9.99
        }
        ]
    },
    "stock": {
        "amount": 6,
        "correctedStock": 5,
        "managedByRetailer": false
    },
    "fulfilment": {
        "method": "FBR",
        "deliveryCode": "24uurs-23",
        "pickUpPoints": [
        {
            "code": "PUP_AH_NL"
        }
        ]
    },
    "store": {
        "productTitle": "Product Title",
        "visible": [
        {
            "countryCode": "NL"
        }
        ]
    },
    "condition": {
        "name": "AS_NEW",
        "category": "SECONDHAND",
        "comment": "Heeft een koffie vlek op de kaft."
    },
    "notPublishableReasons": [
        {
        "code": "4003",
        "description": "The seller is on holiday."
        }
    ]
    }
    """

    UPDATE_AN_OFFER_RESPONSE = """
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

    DELETE_OFFER_BY_ID_RESPONSE = """
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
    UPDATE_PRICE_FOR_OFFER_BY_ID_RESPONSE = """
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

    UPDATE_STOCK_FOR_OFFER_BY_ID_RESPONSE = """
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

    @urlmatch(path=r'/retailer/orders/shipment$')
    def shipments_stub(self, url, request):
        print("REquest Body =========" ,request.body)
        request_body = {
            "orderItems": [
                {
                    "orderItemId": "2012345678"
                }
            ],
            "shipmentReference": "B321SR",
            "transport": {
                "transporterCode": "TNT",
                "trackAndTrace": "3SBOL0987654321"
            }
        }

        # if transporter_code:
        #         payload.setdefault("transport", {})[
        #             "transporterCode"
        #         ] = transporter_code
        #     if track_and_trace:
        #         payload.setdefault("transport", {})[
        #             "trackAndTrace"
        #         ] = track_and_trace
        request_body = json.dumps(request_body).encode('utf-8')
        # request_body_s = decode("utf-8")
        print("REquest Body =========",request_body)
        # assert request.body == request_body
        return self.SHIPMENTS_RESPONSE

    @urlmatch(path=r'/retailer/offers$')
    def create_new_offer_stub(self, url, request):
        print("REquest Body" ,request.body)
        request_body = {
                "ean": "0000007740404",
                "condition": {
                    "name": "AS_NEW",
                    "category": "SECONDHAND",
                    "comment": "Heeft een koffie vlek op de kaft."
                },
                "reference": "REF12345",
                "onHoldByRetailer": False,
                "unknownProductTitle": "Unknown Product Title",
                "pricing": {
                    "bundlePrices": [
                    {
                        "quantity": 1,
                        "unitPrice": 9.99
                    }
                    ]
                },
                "stock": {
                    "amount": 6,
                    "managedByRetailer": False
                },
                "fulfilment": {
                    "method": "FBR",
                    "deliveryCode": "24uurs-23",
                    "pickUpPoints": [
                    {
                        "code": "PUP_AH_NL"
                    }
                    ]
                }
            }
        request_body = json.dumps(request_body).encode('utf-8')
        assert request.body == request_body
        return self.CREATE_NEW_OFFER_RESPONSE

    @urlmatch(path=r'/retailer/offers/export$')
    def request_export_file_stub(self, url, request):
        print("REquest Body =========" ,request.body)
        request_body = {
            "format": "CSV"
        }
        request_body = json.dumps(request_body).encode('utf-8')
        # request_body_s = decode("utf-8")
        print("REquest Body =========",request_body)
        assert request.body == request_body
        return self.REQUEST_OFFER_EXPORT_FILE_RESPONSE
    
    @urlmatch(path=r'retailer/offers/export/987654321$')
    def get_offer_file_stub(self, url, request):
        # print("REquest Body =========" ,request.body)
        # request_body = {
        #     "format": "CSV"
        # }
        # request_body = json.dumps(request_body).encode('utf-8')
        # # request_body_s = decode("utf-8")
        # print("REquest Body =========",request_body)
        # assert request.body == request_body
        # return self.REQUEST_OFFER_EXPORT_FILE_RESPONSE
        return {}
    
    @urlmatch(path=r'/retailer/offers/')
    def retrieve_offer_by_offerid_stub(self, url, request):
        return self.RETRIEVE_OFFER_BY_OFFERID_RESPONSE
    
    @urlmatch(path=r'/retailer/offers/')
    def update_an_offer_stub(self, url, request):
        print("REquest Body =========" ,request.body)
        request_body = {
            "reference": "REF12345",
            "onHoldByRetailer": False,
            "unknownProductTitle": "Unknown Product Title",
            "fulfilment": {
                "method": "FBR",
                "deliveryCode": "24uurs-23",
                "pickUpPoints": [
                {
                    "code": "PUP_AH_NL"
                }
                ]
            }
        }
        request_body = json.dumps(request_body).encode('utf-8')
        # request_body_s = decode("utf-8")
        print("REquest Body =========",request_body)
        assert request.body == request_body
        return self.UPDATE_AN_OFFER_RESPONSE

    @urlmatch(path=r'/retailer/offers/1234567')
    def delete_offer_by_id_stub(self, url, request):
        return self.DELETE_OFFER_BY_ID_RESPONSE

    @urlmatch(path=r'/retailer/offers/1234567')
    def update_price_for_offer_by_id_stub(self, url, request):
        request_body = {
            "pricing": {
                "bundlePrices": [
                {
                    "quantity": 1,
                    "unitPrice": 9.99
                }
                ]
            }
        }
        request_body = json.dumps(request_body).encode('utf-8')
        print("REquest Body =========",request_body)
        assert request.body == request_body
        return self.UPDATE_PRICE_FOR_OFFER_BY_ID_RESPONSE

    @urlmatch(path=r'/retailer/offers/1234567')
    def update_stock_for_offer_by_id_stub(self, url, request):
        request_body = {
            "amount": 6,
            "managedByRetailer": False
        }
        request_body = json.dumps(request_body).encode('utf-8')
        print("REquest Body =========",request_body)
        print("URL", url)
        assert request.body == request_body
        return self.UPDATE_STOCK_FOR_OFFER_BY_ID_RESPONSE

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
            assert order.orderPlacedDateTime == datetime(2017, 2, 9, 12, 39, 48, tzinfo=tzoffset(None, 3600))

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

            assert orById.orderPlacedDateTime == datetime(2017, 2, 9, 12, 39, 48, tzinfo=tzoffset(None, 3600))

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
            assert item.fulfilment.method == "FBR"
            assert item.fulfilment.distributionParty == "RETAILER"
            # assert isinstance(item.fulfilment.latestDeliveryDate, datetime)
            assert item.fulfilment.latestDeliveryDate == date(2017, 2, 10)
            # assert item.fulfilment.latestDeliveryDate == date(2017, 2, 10)
            assert item.fulfilment.exactDeliveryDate == date(2017, 2, 13)
            assert item.fulfilment.expiryDate == date(2017, 2, 13)
            assert item.offer.offerId == "6ff736b5-cdd0-4150-8c67-78269ee986f5"
            assert item.offer.reference == "BOLCOM00123"
            assert item.product.ean == "0000007740404"
            assert item.product.title == "Product Title"
            assert isinstance(item.quantity, int)
            assert item.quantity == 10
            # assert isinstance(item.unitPrice, float)
            print("Unit price", item.unitPrice)
            assert item.unitPrice == Decimal('12.99')
            assert item.commission == Decimal('5.18')
            itemAdd = item.additionalServices[0]
            print(itemAdd)
            assert itemAdd.serviceType == "PLACEMENT_AND_INSTALLATION"
    
    #Orders Cancellation
    def test_orders_cancellation(self): 
        with HTTMock(self.orders_cancellation_stub):
            cancle_order = self.api.orders.cancel_order_item(order_item_id = '2012345678', reason_code = "BAD_CONDITION")
            print(dir(cancle_order))

            assert cancle_order.id == 1234567
            assert cancle_order.entityId == "987654321"
            assert cancle_order.eventType == "CONFIRM_SHIPMENT"
            assert cancle_order.description == "Example process status description for processing 987654321."
            assert cancle_order.status == "SUCCESS"
            assert cancle_order.errorMessage == "Example process status error message."
            assert cancle_order.createTimestamp == datetime(2018, 11, 14, 9, 34, 41, tzinfo=tzoffset(None, 3600))
            link = cancle_order.links[0]
            assert link.rel == "self"
            assert link.href == "https://api.bol.com/retailer/process-status/1234567"
            assert link.method == "GET"

    # Ship order item
    def test_ship_order_item(self):
        with HTTMock(self.shipments_stub):
            ship_order_items = self.api.orders.ship_order_item(
                                        order_item_id="2012345678",
                                        shipment_reference="B321SR",
                                        # shipping_label_id="d4c50077-0c19-435f-9bee-1b30b9f4ba1a",
                                        transporter_code="TNT",
                                        track_and_trace="3SBOL0987654321",
                                    )
            print("Ship Order Item", ship_order_items)
            assert ship_order_items.id == 1234567
            assert ship_order_items.entityId == "987654321"
            assert ship_order_items.eventType == "CONFIRM_SHIPMENT"
            assert ship_order_items.description == "Example process status description for processing 987654321."
            assert ship_order_items.status == "SUCCESS"
            assert ship_order_items.errorMessage == "Example process status error message."
            assert ship_order_items.createTimestamp == datetime(2018, 11, 14, 9, 34, 41, tzinfo=tzoffset(None, 3600))
            link = ship_order_items.links[0]
            assert link.rel == "self"
            assert link.href == "https://api.bol.com/retailer/process-status/1234567"
            assert link.method == "GET"

    def test_create_new_offer(self):
        with HTTMock(self.create_new_offer_stub):
            data = {
                "ean": "0000007740404",
                "condition": {
                    "name": "AS_NEW",
                    "category": "SECONDHAND",
                    "comment": "Heeft een koffie vlek op de kaft."
                },
                "reference": "REF12345",
                "onHoldByRetailer": False,
                "unknownProductTitle": "Unknown Product Title",
                "pricing": {
                    "bundlePrices": [
                    {
                        "quantity": 1,
                        "unitPrice": 9.99
                    }
                    ]
                },
                "stock": {
                    "amount": 6,
                    "managedByRetailer": False
                },
                "fulfilment": {
                    "method": "FBR",
                    "deliveryCode": "24uurs-23",
                    "pickUpPoints": [
                    {
                        "code": "PUP_AH_NL"
                    }
                    ]
                }
            }
            create_offer= self.api.offers.createSingleOffer(data)
            print(dir(create_offer))
            assert create_offer.id == 1234567
            assert create_offer.entityId == "987654321"
            assert create_offer.eventType == "CONFIRM_SHIPMENT"
            assert create_offer.description == "Example process status description for processing 987654321."
            assert create_offer.status == "SUCCESS"
            assert create_offer.errorMessage == "Example process status error message."
            assert create_offer.createTimestamp == datetime(2018, 11, 14, 9, 34, 41, tzinfo=tzoffset(None, 3600))
            link = create_offer.links[0]
            assert link.rel == "self"
            assert link.href == "https://api.bol.com/retailer/process-status/1234567"
            assert link.method == "GET"

    def test_request_export_file(self):
        with HTTMock(self.request_export_file_stub):
            request_export_file = self.api.offers.requestExportFile()
            print(dir(request_export_file))
            assert request_export_file.id == 1234567
            assert request_export_file.entityId == "987654321"
            assert request_export_file.eventType == "CONFIRM_SHIPMENT"
            assert request_export_file.description == "Example process status description for processing 987654321."
            assert request_export_file.status == "SUCCESS"
            assert request_export_file.errorMessage == "Example process status error message."
            assert request_export_file.createTimestamp == datetime(2018, 11, 14, 9, 34, 41, tzinfo=tzoffset(None, 3600))
            link = request_export_file.links[0]
            assert link.rel == "self"
            assert link.href == "https://api.bol.com/retailer/process-status/1234567"
            assert link.method == "GET"
  
    # def test_get_offer_file(self):
    #     with HTTMock(self.get_offer_file_stub):
            # process_status_by_id = self.api.process_status.getById("1234567")
            # print("ID details", process_status_by_id)
            # request_export_file = self.api.offers.getOffersFile("987654321")
            # print("This is get offers file response", request_export_file)

    def test_retrieve_offer_by_offerid(self):
        with HTTMock(self.retrieve_offer_by_offerid_stub):
            retrieve_offer_by_offerid = self.api.offers.getSingleOffer("6ff736b5-cdd0-4150-8c67-78269ee986f5")
            print(dir(retrieve_offer_by_offerid))
            assert retrieve_offer_by_offerid.offerId == "6ff736b5-cdd0-4150-8c67-78269ee986f5"
            assert retrieve_offer_by_offerid.ean == "0000007740404"
            assert retrieve_offer_by_offerid.reference == "REF12345"
            assert retrieve_offer_by_offerid.onHoldByRetailer == False
            assert retrieve_offer_by_offerid.unknownProductTitle == "Unknown Product Title"
            print("price",dir(retrieve_offer_by_offerid.pricing.bundlePrices))
            pricing = retrieve_offer_by_offerid.pricing.bundlePrices[0]
            assert pricing.quantity == 1
            assert pricing.unitPrice == Decimal('9.99')
            stock = retrieve_offer_by_offerid.stock
            print("This is stock ===",dir(stock))
            assert stock.amount == 6
            assert stock.correctedStock == 5
            assert stock.managedByRetailer == False
            fulfilment = retrieve_offer_by_offerid.fulfilment
            assert fulfilment.method == "FBR"
            assert fulfilment.deliveryCode == "24uurs-23"
            pickup = fulfilment.pickUpPoints[0]
            assert pickup.code == "PUP_AH_NL"
            assert retrieve_offer_by_offerid.store.productTitle == "Product Title"
            assert retrieve_offer_by_offerid.store.visible[0].countryCode == "NL"
            condition = retrieve_offer_by_offerid.condition
            assert condition.name == "AS_NEW"
            assert condition.category == "SECONDHAND"
            assert condition.comment == "Heeft een koffie vlek op de kaft."
            reason = retrieve_offer_by_offerid.notPublishableReasons[0]
            assert reason.code == "4003"
            assert reason.description == "The seller is on holiday."
    
    def test_update_an_offer(self):
        with HTTMock(self.update_an_offer_stub):
            data = {
                "reference": "REF12345",
                "onHoldByRetailer": False,
                "unknownProductTitle": "Unknown Product Title",
                "fulfilment": {
                    "method": "FBR",
                    "deliveryCode": "24uurs-23",
                    "pickUpPoints": [
                    {
                        "code": "PUP_AH_NL"
                    }
                    ]
                }
            }
            update_an_offer = self.api.offers.updateProduct("1234567", data)
            print(dir(update_an_offer))

            assert update_an_offer.id == 1234567
            assert update_an_offer.entityId == "987654321"
            assert update_an_offer.eventType == "CONFIRM_SHIPMENT"
            assert update_an_offer.description == "Example process status description for processing 987654321."
            assert update_an_offer.status == "SUCCESS"
            assert update_an_offer.errorMessage == "Example process status error message."
            assert update_an_offer.createTimestamp == datetime(2018, 11, 14, 9, 34, 41, tzinfo=tzoffset(None, 3600))
            link = update_an_offer.links[0]
            assert link.rel == "self"
            assert link.href == "https://api.bol.com/retailer/process-status/1234567"
            assert link.method == "GET"

    def test_delete_offer_by_id(self):
        with HTTMock(self.delete_offer_by_id_stub):
            update_an_offer = self.api.offers.deleteOffers("1234567")
            print(dir(update_an_offer))
            assert update_an_offer.id == 1234567
            assert update_an_offer.entityId == "987654321"
            assert update_an_offer.eventType == "CONFIRM_SHIPMENT"
            assert update_an_offer.description == "Example process status description for processing 987654321."
            assert update_an_offer.status == "SUCCESS"
            assert update_an_offer.errorMessage == "Example process status error message."
            assert update_an_offer.createTimestamp == datetime(2018, 11, 14, 9, 34, 41, tzinfo=tzoffset(None, 3600))
            link = update_an_offer.links[0]
            assert link.rel == "self"
            assert link.href == "https://api.bol.com/retailer/process-status/1234567"
            assert link.method == "GET"

    def test_update_price_for_offer_by_id(self):
        with HTTMock(self.update_price_for_offer_by_id_stub):
            data = {
                "pricing": {
                    "bundlePrices": [
                    {
                        "quantity": 1,
                        "unitPrice": 9.99
                    }
                    ]
                }
            }
            update_price_for_offer_by_id = self.api.offers.updateProductPrice("1234567", data)
            print(dir(update_price_for_offer_by_id))
            assert update_price_for_offer_by_id.id == 1234567
            assert update_price_for_offer_by_id.entityId == "987654321"
            assert update_price_for_offer_by_id.eventType == "CONFIRM_SHIPMENT"
            assert update_price_for_offer_by_id.description == "Example process status description for processing 987654321."
            assert update_price_for_offer_by_id.status == "SUCCESS"
            assert update_price_for_offer_by_id.errorMessage == "Example process status error message."
            assert update_price_for_offer_by_id.createTimestamp == datetime(2018, 11, 14, 9, 34, 41, tzinfo=tzoffset(None, 3600))
            link = update_price_for_offer_by_id.links[0]
            assert link.rel == "self"
            assert link.href == "https://api.bol.com/retailer/process-status/1234567"
            assert link.method == "GET"

    def test_update_stock_for_offer_by_id(self):
        with HTTMock(self.update_stock_for_offer_by_id_stub):
            data = {
                "amount": 6,
                "managedByRetailer": False
            }
            update_stock_for_offer_by_id = self.api.offers.updateProductStock("1234567", data)
            print(dir(update_stock_for_offer_by_id))
            assert update_stock_for_offer_by_id.id == 1234567
            assert update_stock_for_offer_by_id.entityId == "987654321"
            assert update_stock_for_offer_by_id.eventType == "CONFIRM_SHIPMENT"
            assert update_stock_for_offer_by_id.description == "Example process status description for processing 987654321."
            assert update_stock_for_offer_by_id.status == "SUCCESS"
            assert update_stock_for_offer_by_id.errorMessage == "Example process status error message."
            assert update_stock_for_offer_by_id.createTimestamp == datetime(2018, 11, 14, 9, 34, 41, tzinfo=tzoffset(None, 3600))
            link = update_stock_for_offer_by_id.links[0]
            assert link.rel == "self"
            assert link.href == "https://api.bol.com/retailer/process-status/1234567"
            assert link.method == "GET"