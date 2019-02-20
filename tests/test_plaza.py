import pytest

from decimal import Decimal
from datetime import datetime
from dateutil.tz import tzoffset

from bol.plaza.api import PlazaAPI, TransporterCode

from httmock import HTTMock, urlmatch


ORDERS_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<bns:Orders
    xmlns:bns="http://plazaapi.bol.com/services/xsd/plazaapiservice-1.0.xsd">
  <bns:Order>
    <bns:OrderId>123</bns:OrderId>
    <bns:DateTimeCustomer>2015-09-23T12:30:36</bns:DateTimeCustomer>
    <bns:DateTimeDropShipper>2015-09-23T12:30:36</bns:DateTimeDropShipper>
    <bns:CustomerDetails>
      <bns:ShipmentDetails>
        <bns:SalutationCode>01</bns:SalutationCode>
        <bns:Firstname>Jan</bns:Firstname>
        <bns:Surname>Janssen</bns:Surname>
        <bns:Streetname>Shipmentstraat</bns:Streetname>
        <bns:Housenumber>42</bns:Housenumber>
        <bns:HousenumberExtended>bis</bns:HousenumberExtended>
        <bns:AddressSupplement>3 hoog achter</bns:AddressSupplement>
        <bns:ZipCode>1000 AA</bns:ZipCode>
        <bns:City>Amsterdam</bns:City>
        <bns:CountryCode>NL</bns:CountryCode>
        <bns:Email>nospam4me@myaccount.com</bns:Email>
        <bns:DeliveryPhoneNumber>12345</bns:DeliveryPhoneNumber>
        <bns:Company>The Company</bns:Company>
      </bns:ShipmentDetails>
      <bns:BillingDetails>
        <bns:SalutationCode>02</bns:SalutationCode>
        <bns:Firstname>Jans</bns:Firstname>
        <bns:Surname>Janssen</bns:Surname>
        <bns:Streetname>Billingstraat</bns:Streetname>
        <bns:Housenumber>1</bns:Housenumber>
        <bns:HousenumberExtended>a</bns:HousenumberExtended>
        <bns:AddressSupplement>Onder de brievenbus</bns:AddressSupplement>
        <bns:ZipCode>5000 ZZ</bns:ZipCode>
        <bns:City>Amsterdam</bns:City>
        <bns:CountryCode>NL</bns:CountryCode>
        <bns:Email>dontemail@me.net</bns:Email>
        <bns:DeliveryPhoneNumber>67890</bns:DeliveryPhoneNumber>
        <bns:Company>Bol.com</bns:Company>
      </bns:BillingDetails>
    </bns:CustomerDetails>
    <bns:OrderItems>
      <bns:OrderItem>
        <bns:OrderItemId>123</bns:OrderItemId>
        <bns:EAN>9789062387410</bns:EAN>
        <bns:OfferReference>PARTNERREF001</bns:OfferReference>
        <bns:Title>Regelmaat en Inbakeren</bns:Title>
        <bns:Quantity>1</bns:Quantity>
        <bns:OfferPrice>123.45</bns:OfferPrice>
        <bns:PromisedDeliveryDate>Binnen 24 uur</bns:PromisedDeliveryDate>
        <bns:TransactionFee>19.12</bns:TransactionFee>
      </bns:OrderItem>
    </bns:OrderItems>
  </bns:Order>
</bns:Orders>"""


PAYMENTS_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<bns:Payments
    xmlns:bns="http://plazaapi.bol.com/services/xsd/plazaapiservice-1.0.xsd">
  <bns:Payment>
    <bns:CreditInvoiceNumber>123</bns:CreditInvoiceNumber>
    <bns:DateTimePayment>2015-09-23T21:35:43</bns:DateTimePayment>
    <bns:PaymentAmount>425.77</bns:PaymentAmount>
    <bns:PaymentShipments>
      <bns:PaymentShipment>
        <bns:ShipmentId>456</bns:ShipmentId>
        <bns:OrderId>123001</bns:OrderId>
        <bns:PaymentShipmentAmount>425.77</bns:PaymentShipmentAmount>
        <bns:PaymentStatus>FINAL</bns:PaymentStatus>
        <bns:ShipmentDate>2015-09-23T21:35:43</bns:ShipmentDate>
        <bns:PaymentShipmentItems>
          <bns:PaymentShipmentItem>
            <bns:OrderItemId>123001001</bns:OrderItemId>
            <bns:EAN>9789062387410</bns:EAN>
            <bns:OfferReference>PARTNERREF001</bns:OfferReference>
            <bns:Quantity>1</bns:Quantity>
            <bns:OfferPrice>425.77</bns:OfferPrice>
            <bns:ShippingContribution>1.95</bns:ShippingContribution>
            <bns:TransactionFee>10.00</bns:TransactionFee>
            <bns:TotalAmount>425.77</bns:TotalAmount>
            <bns:ShipmentStatus>NORMAL</bns:ShipmentStatus>
          </bns:PaymentShipmentItem>
        </bns:PaymentShipmentItems>
      </bns:PaymentShipment>
    </bns:PaymentShipments>
  </bns:Payment>
</bns:Payments>"""


SHIPMENTS_RESPONSE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Shipments xmlns="https://plazaapi.bol.com/services/xsd/v2/plazaapi.xsd">
    <Shipment>
        <ShipmentId>123</ShipmentId>
        <ShipmentDate>2016-09-19T18:21:59.324+02:00</ShipmentDate>
        <ExpectedDeliveryDate>2016-09-19+02:00</ExpectedDeliveryDate>
        <ShipmentReference>shipmentReferentie</ShipmentReference>
        <ShipmentItems>
            <ShipmentItem>
                <OrderItem>
                    <OrderItemId>5612423</OrderItemId>
                    <OrderId>7464</OrderId>
                    <OrderItemSequenceNumber>2</OrderItemSequenceNumber>
                    <OrderDate>2016-09-17T18:21:59.324+02:00</OrderDate>
                    <PromisedDeliveryDate>2016-09-20+02:00</PromisedDeliveryDate>
                    <EAN>9789062387410</EAN>
                    <Title>Harry Potter</Title>
                    <Quantity>1</Quantity>
                    <OfferPrice>123.45</OfferPrice>
                    <OfferCondition>NEW</OfferCondition>
                    <OfferReference>MijnOffer 123</OfferReference>
                    <FulfilmentMethod>FBR</FulfilmentMethod>
                </OrderItem>
            </ShipmentItem>
        </ShipmentItems>
        <Transport>
            <TransportId>8444626</TransportId>
            <TransporterCode>DHLFORYOU</TransporterCode>
            <TrackAndTrace>3stest</TrackAndTrace>
            <ShippingLabelId>349</ShippingLabelId>
        </Transport>
        <CustomerDetails>
            <FirstName>Jan</FirstName>
            <Surname>Janssen</Surname>
            <Streetname>Vogelstraat</Streetname>
            <Housenumber>42</Housenumber>
            <HousenumberExtended>bis</HousenumberExtended>
            <AddressSupplement>3 hoog achter</AddressSupplement>
            <ExtraAddressInformation>extra adres info</ExtraAddressInformation>
            <ZipCode>1000 AA</ZipCode>
            <City>Amsterdam</City>
            <CountryCode>NL</CountryCode>
            <Email>nospam4me@myaccount.com</Email>
            <DeliveryPhoneNumber>12345</DeliveryPhoneNumber>
            <Company>The Company</Company>
            <VatNumber>VatNumber12</VatNumber>
        </CustomerDetails>
    </Shipment>
    <Shipment>
        <ShipmentDate>2016-09-19T18:21:59.325+02:00</ShipmentDate>
        <ShipmentItems>
            <ShipmentItem>
                <OrderItem>
                    <OrderItemId>8812523</OrderItemId>
                    <OrderId>7464</OrderId>
                    <OrderItemSequenceNumber>2</OrderItemSequenceNumber>
                    <OrderDate>2016-09-17T18:21:59.325+02:00</OrderDate>
                    <EAN>9789062387410</EAN>
                    <Quantity>1</Quantity>
                    <OfferPrice>123.45</OfferPrice>
                    <OfferCondition>NEW</OfferCondition>
                    <FulfilmentMethod>FBR</FulfilmentMethod>
                </OrderItem>
            </ShipmentItem>
        </ShipmentItems>
        <Transport>
            <ShippingLabelId>1807</ShippingLabelId>
        </Transport>
        <CustomerDetails>
            <FirstName>Jan</FirstName>
            <Surname>Janssen</Surname>
            <Streetname>Vogelstraat</Streetname>
            <Housenumber>42</Housenumber>
            <ZipCode>1000 AA</ZipCode>
            <City>Amsterdam</City>
            <CountryCode>NL</CountryCode>
            <Email>nospam4me@myaccount.com</Email>
        </CustomerDetails>
    </Shipment>
</Shipments>
"""


CREATE_SHIPMENT_RESPONSE = \
    """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns1:ProcessStatus
    xmlns:ns1="https://plazaapi.bol.com/services/xsd/v2/plazaapi.xsd">
    <ns1:id>0</ns1:id>
    <ns1:sellerId>12345678</ns1:sellerId>
    <ns1:entityId>123</ns1:entityId>
    <ns1:eventType>CONFIRM_SHIPMENT</ns1:eventType>
    <ns1:description>Confirm shipment for order item 123.</ns1:description>
    <ns1:status>PENDING</ns1:status>
</ns1:ProcessStatus>
"""

UPDATE_TRANSPORT_RESPONSE = \
    """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns1:ProcessStatus
     xmlns:ns1="https://plazaapi.bol.com/services/xsd/v2/plazaapi.xsd">
     <ns1:id>0</ns1:id>
     <ns1:sellerId>925853</ns1:sellerId>
     <ns1:entityId>1</ns1:entityId>
     <ns1:eventType>CHANGE_TRANSPORT</ns1:eventType>
     <ns1:description>Change transport with id 1.</ns1:description>
     <ns1:status>PENDING</ns1:status>
</ns1:ProcessStatus>
"""


@urlmatch(path=r'/services/rest/orders/v2$')
def orders_stub(url, request):
    return ORDERS_RESPONSE


@urlmatch(path=r'/services/rest/payments/v2/201501$')
def payments_stub(url, request):
    return PAYMENTS_RESPONSE


@urlmatch(path=r'/services/rest/shipments/v2$')
def shipments_stub(url, request):
    return SHIPMENTS_RESPONSE


def test_orders():
    with HTTMock(orders_stub):
        api = PlazaAPI('api_key', 'api_secret', test=True)
        orders = api.orders.list()
        assert len(orders) == 1

        order = orders[0]
        assert order.OrderId == '123'

        assert order.CustomerDetails.BillingDetails.SalutationCode == 2
        assert order.CustomerDetails.BillingDetails.Firstname == 'Jans'
        assert order.CustomerDetails.BillingDetails.Surname == 'Janssen'
        assert (
            order.CustomerDetails.BillingDetails.Streetname ==
            'Billingstraat')
        assert order.CustomerDetails.BillingDetails.Housenumber == 1
        assert order.CustomerDetails.BillingDetails.HousenumberExtended == 'a'
        assert (
            order.CustomerDetails.BillingDetails.AddressSupplement ==
            'Onder de brievenbus')
        assert order.CustomerDetails.BillingDetails.ZipCode == '5000 ZZ'
        assert order.CustomerDetails.BillingDetails.City == 'Amsterdam'
        assert order.CustomerDetails.BillingDetails.CountryCode == 'NL'
        assert order.CustomerDetails.BillingDetails.Email == 'dontemail@me.net'
        assert (
            order.CustomerDetails.BillingDetails.DeliveryPhoneNumber ==
            '67890')
        assert order.CustomerDetails.BillingDetails.Company == 'Bol.com'

        assert order.CustomerDetails.ShipmentDetails.SalutationCode == 1
        assert order.CustomerDetails.ShipmentDetails.Firstname == 'Jan'
        assert order.CustomerDetails.ShipmentDetails.Surname == 'Janssen'
        assert (
            order.CustomerDetails.ShipmentDetails.Streetname ==
            'Shipmentstraat')
        assert order.CustomerDetails.ShipmentDetails.Housenumber == 42
        assert (
            order.CustomerDetails.ShipmentDetails.HousenumberExtended == 'bis')

        assert (
            order.CustomerDetails.ShipmentDetails.AddressSupplement ==
            '3 hoog achter')
        assert order.CustomerDetails.ShipmentDetails.ZipCode == '1000 AA'
        assert order.CustomerDetails.ShipmentDetails.City == 'Amsterdam'
        assert order.CustomerDetails.ShipmentDetails.CountryCode == 'NL'
        assert (
            order.CustomerDetails.ShipmentDetails.Email ==
            'nospam4me@myaccount.com')
        assert (
            order.CustomerDetails.ShipmentDetails.DeliveryPhoneNumber ==
            '12345')
        assert order.CustomerDetails.ShipmentDetails.Company == 'The Company'

        assert len(order.OrderItems) == 1
        item = order.OrderItems[0]

        assert item.OrderItemId == '123'
        assert item.EAN == '9789062387410'
        assert item.OfferReference == 'PARTNERREF001'
        assert item.Title == 'Regelmaat en Inbakeren'
        assert item.Quantity == 1
        assert item.OfferPrice == Decimal('123.45')
        assert item.PromisedDeliveryDate == 'Binnen 24 uur'
        assert item.TransactionFee == Decimal('19.12')


def test_order_process():
    @urlmatch(path=r'/services/rest/shipments/v2$')
    def create_shipment_stub(url, request):
        assert request.body == """<?xml version="1.0" encoding="UTF-8"?>
<ShipmentRequest xmlns="https://plazaapi.bol.com/services/xsd/v2/plazaapi.xsd">
    <DateTime>2016-10-01T01:08:17</DateTime>
    <OrderItemId>123</OrderItemId>
    <ShipmentReference>abc</ShipmentReference>
    <Transport>
        <TrackAndTrace>3S123</TrackAndTrace>
        <TransporterCode>GLS</TransporterCode>
    </Transport>
</ShipmentRequest>
"""
        return CREATE_SHIPMENT_RESPONSE

    with HTTMock(create_shipment_stub):
        api = PlazaAPI('api_key', 'api_secret', test=True)
        dt = datetime(2016, 10, 1, 1, 8, 17, 0)
        process_status = api.shipments.create(
            order_item_id='123',
            date_time=dt,
            expected_delivery_date=None,
            shipment_reference='abc',
            transporter_code=TransporterCode.GLS,
            track_and_trace='3S123')
        assert process_status.sellerId == 12345678


def test_payments():
    with HTTMock(payments_stub):
        api = PlazaAPI('api_key', 'api_secret', test=True)
        payments = api.payments.list(2015, 1)

        assert len(payments) == 1
        payment = payments[0]
        assert payment.PaymentAmount == Decimal('425.77')
        assert payment.DateTimePayment == datetime(2015, 9, 23, 21, 35, 43)
        assert payment.CreditInvoiceNumber == '123'
        assert len(payment.PaymentShipments) == 1
        shipment = payment.PaymentShipments[0]
        assert shipment.OrderId == '123001'
        assert shipment.ShipmentId == '456'
        assert shipment.PaymentShipmentAmount == Decimal('425.77')
        assert shipment.PaymentStatus == 'FINAL'


def test_shipments():
    with HTTMock(shipments_stub):
        api = PlazaAPI('api_key', 'api_secret', test=True)
        shipments = api.shipments.list(1)

        assert len(shipments) == 2
        shipment = shipments[0]
        assert shipment.ShipmentDate == datetime(
            2016, 9, 19, 18, 21, 59, 324000, tzinfo=tzoffset(None, 7200))
        assert shipment.ExpectedDeliveryDate == datetime(
            2016, 9, 19, 0, 0, tzinfo=tzoffset(None, 7200))


def test_update_transport():
    @urlmatch(path=r'/services/rest/transports/v2/1$')
    def create_transport_stub(url, request):
        assert request.body == """<?xml version="1.0" encoding="UTF-8"?>
<ChangeTransportRequest xmlns=\
"https://plazaapi.bol.com/services/xsd/v2/plazaapi.xsd">
    <TrackAndTrace>3S123</TrackAndTrace>
    <TransporterCode>GLS</TransporterCode>
</ChangeTransportRequest>
"""
        return UPDATE_TRANSPORT_RESPONSE

    with HTTMock(create_transport_stub):
        api = PlazaAPI('api_key', 'api_secret', test=True)
        process_status = api.transports.update(
            1,
            track_and_trace='3S123',
            transporter_code=TransporterCode.GLS)
        assert process_status.sellerId == 925853


# dreambits testing code

INVENTORY_RESPONSE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<InventoryResponse
xmlns="https://plazaapi.bol.com/services/xsd/v1/plazaapi.xsd">
 <TotalCount>144</TotalCount>
 <TotalPageCount>3</TotalPageCount>
 <Offers>
  <Offer>
   <EAN>9789076174143</EAN>
   <BSKU>1230000402640</BSKU>
   <Title>Harry Potter en de gevangene van Azkaban</Title>
   <Stock>0</Stock>
   <NCK-Stock>1</NCK-Stock>
  </Offer>
  <Offer>
   <EAN>9789076174198</EAN>
   <BSKU>1230000425793</BSKU>
   <Title>Harry Potter &amp; de Vuurbeker</Title>
   <Stock>2</Stock>
   <NCK-Stock>0</NCK-Stock>
  </Offer>
  <Offer>
   <EAN>9789061697664</EAN>
   <BSKU>1230000889762</BSKU>
   <Title>Harry Potter en de halfbloed Prins</Title>
   <Stock>8</Stock>
   <NCK-Stock>0</NCK-Stock>
  </Offer>
  <Offer>
   <EAN>9789061697008</EAN>
   <BSKU>2950000418559</BSKU>
   <Title>Harry Potter en de orde van de Feniks</Title>
   <Stock>1</Stock>
   <NCK-Stock>0</NCK-Stock>
  </Offer>
  <Offer>
   <EAN>9781781103524</EAN>
   <BSKU>1230000425830</BSKU>
   <Title>Harry Potter en de Relieken van de Dood</Title>
   <Stock>20</Stock>
   <NCK-Stock>0</NCK-Stock>
  </Offer>
 </Offers>
</InventoryResponse>"""


def test_get_inventory():

    @urlmatch(path=r'/services/rest/inventory')
    def inventory_stub(url, request):
        return INVENTORY_RESPONSE

    with HTTMock(inventory_stub):
        api = PlazaAPI('api_key', 'api_secret', test=True)
        inventory = api.inventory.getInventory(page=1, quantity="0-250",
                                               state="saleable",
                                               query="0042491966861")

        assert inventory.TotalCount == 144
        offer = inventory.Offers[0]
        assert type(offer.EAN) == str
        assert getattr(offer, "NCK-Stock") == "1"


SINGLE_BOUND_RESPONSE = """<?xml version="1.0" encoding="UTF-8"
standalone="yes"?>
<Inbound xmlns="https://plazaapi.bol.com/services/xsd/v1/plazaapi.xsd">
  <Id>1124284930</Id>
  <Reference>FBB20170726</Reference>
  <CreationDate>2017-07-26T10:58:17.079+02:00</CreationDate>
  <State>ArrivedAtWH</State>
  <LabellingService>false</LabellingService>
  <AnnouncedBSKUs>69</AnnouncedBSKUs>
  <AnnouncedQuantity>237</AnnouncedQuantity>
  <ReceivedBSKUs>69</ReceivedBSKUs>
  <ReceivedQuantity>240</ReceivedQuantity>
  <Products>
    <Product>
      <EAN>4034398404139</EAN>
      <BSKU>2950002126612</BSKU>
      <AnnouncedQuantity>6</AnnouncedQuantity>
      <ReceivedQuantity>6</ReceivedQuantity>
      <State>Announced</State>
  </Product>
  <Product>
      <EAN>4034398400902</EAN>
      <BSKU>2950002125622</BSKU>
      <AnnouncedQuantity>8</AnnouncedQuantity>
      <ReceivedQuantity>8</ReceivedQuantity>
      <State>Announced</State>
  </Product>
  <Product>
      <EAN>4034398209925</EAN>
      <BSKU>2950002126148</BSKU>
      <AnnouncedQuantity>3</AnnouncedQuantity>
      <ReceivedQuantity>3</ReceivedQuantity>
      <State>Announced</State>
  </Product>
  <Product>
      <EAN>4034398400964</EAN>
      <BSKU>2950002126896</BSKU>
      <AnnouncedQuantity>1</AnnouncedQuantity>
      <ReceivedQuantity>1</ReceivedQuantity>
      <State>Announced</State>
    </Product>
  </Products>
  <StateTransitions>
    <InboundState>
      <State>ArrivedAtWH</State>
      <StateDate>2017-07-28T09:26:23.371+02:00</StateDate>
    </InboundState>
    <InboundState>
      <State>PreAnnounced</State>
      <StateDate>2017-07-26T11:16:10.757+02:00</StateDate>
    </InboundState>
    <InboundState>
      <State>Draft</State>
      <StateDate>2017-07-26T10:58:17.925+02:00</StateDate>
    </InboundState>
  </StateTransitions>
  <TimeSlot>
    <Start>2017-07-28T06:00:00.000+02:00</Start>
    <End>2017-07-28T19:00:00.000+02:00</End>
  </TimeSlot>
  <FbbTransporter>
    <Name>PostNL</Name>
    <Code>PostNL</Code>
  </FbbTransporter>
</Inbound>"""


def test_get_single_inbound():

    @urlmatch(path=r'/services/rest/inbounds/1124284930$')
    def single_inbound_stub(url, request):
        return SINGLE_BOUND_RESPONSE

    with HTTMock(single_inbound_stub):
        api = PlazaAPI('api_key', 'api_secret', test=True)
        single_inbound = api.inbounds.getSingleInbound(inbound_id=1124284930)

        assert isinstance(single_inbound.LabellingService, bool)
        product = single_inbound.Products[0]
        assert isinstance(product.AnnouncedQuantity, int)
        assert not isinstance(product.AnnouncedQuantity, str)
        assert not isinstance(product.AnnouncedQuantity, str)
        assert single_inbound.FbbTransporter.Name == "PostNL"
        assert single_inbound.FbbTransporter.Code == "PostNL"
        inboundStat = single_inbound.StateTransitions[0]
        assert inboundStat.State == "ArrivedAtWH"


ALL_BOUND_RESPONSE = """<?xml version="1.0" encoding="UTF-8"
standalone="yes"?>
<Inbounds xmlns="https://plazaapi.bol.com/services/xsd/v1/plazaapi.xsd">
  <TotalCount>4</TotalCount>
  <TotalPageCount>1</TotalPageCount>
      <Inbound>
        <Id>1124284930</Id>
        <Reference>FBB20170726</Reference>
        <CreationDate>2017-07-26T10:58:17.079+02:00</CreationDate>
        <State>ArrivedAtWH</State>
        <LabellingService>false</LabellingService>
        <AnnouncedBSKUs>69</AnnouncedBSKUs>
        <AnnouncedQuantity>237</AnnouncedQuantity>
        <ReceivedBSKUs>69</ReceivedBSKUs>
        <ReceivedQuantity>240</ReceivedQuantity>
        <TimeSlot>
          <Start>2017-07-28T06:00:00.000+02:00</Start>
          <End>2017-07-28T19:00:00.000+02:00</End>
        </TimeSlot>
        <FbbTransporter>
          <Name>PostNL</Name>
          <Code>PostNL</Code>
        </FbbTransporter>
      </Inbound>
      <Inbound>
        <Id>1124284929</Id>
        <Reference>FBB20170712</Reference>
        <CreationDate>2017-07-12T21:08:02.433+02:00</CreationDate>
        <State>ArrivedAtWH</State>
        <LabellingService>false</LabellingService>
        <AnnouncedBSKUs>85</AnnouncedBSKUs>
        <AnnouncedQuantity>204</AnnouncedQuantity>
        <ReceivedBSKUs>90</ReceivedBSKUs>
        <ReceivedQuantity>203</ReceivedQuantity>
        <TimeSlot>
          <Start>2017-07-17T06:00:00.000+02:00</Start>
          <End>2017-07-17T19:00:00.000+02:00</End>
        </TimeSlot>
        <FbbTransporter>
          <Name>PostNL</Name>
          <Code>PostNL</Code>
        </FbbTransporter>
      </Inbound>
</Inbounds>"""


def test_get_all_inbound():

    @urlmatch(path=r'/services/rest/inbounds$')
    def all_inbound_stub(url, request):
        return ALL_BOUND_RESPONSE

    with HTTMock(all_inbound_stub):
        api = PlazaAPI('api_key', 'api_secret', test=True)
        all_inbound = api.inbounds.getAllInbounds(page=1)

        inbound = all_inbound.AllInbound[0]
        assert isinstance(inbound.Reference, str)
        assert isinstance(inbound.State, str)
        assert inbound.State == "ArrivedAtWH"
        assert inbound.Id == "1124284930"
        assert isinstance(inbound.LabellingService, bool)
        assert not inbound.LabellingService
        assert inbound.AnnouncedBSKUs == 69
        assert inbound.AnnouncedQuantity == 237
        assert inbound.ReceivedBSKUs == 69
        assert inbound.ReceivedQuantity == 240
        assert isinstance(inbound.FbbTransporter.Name, str)
        assert isinstance(inbound.FbbTransporter.Code, str)
        assert inbound.FbbTransporter.Name == "PostNL"
        assert inbound.FbbTransporter.Code == "PostNL"


DELIVERY_WINDOW_RESPONSE = """<?xml version="1.0" encoding="UTF-8"
standalone="yes"?>
<DeliveryWindow xmlns="https://plazaapi.bol.com/services/xsd/v1/plazaapi.xsd">
  <TimeSlot>
    <Start>2017-08-16T07:00:00+02:00</Start>
    <End>2017-08-16T08:00:00+02:00</End>
  </TimeSlot>
  <TimeSlot>
    <Start>2017-08-16T08:00:00+02:00</Start>
    <End>2017-08-16T09:00:00+02:00</End>
  </TimeSlot>
  <TimeSlot>
    <Start>2017-08-16T09:00:00+02:00</Start>
    <End>2017-08-16T10:00:00+02:00</End>
  </TimeSlot>
  <TimeSlot>
    <Start>2017-08-16T10:00:00+02:00</Start>
    <End>2017-08-16T11:00:00+02:00</End>
  </TimeSlot>
  <TimeSlot>
    <Start>2017-08-16T11:00:00+02:00</Start>
    <End>2017-08-16T12:00:00+02:00</End>
  </TimeSlot>
  <TimeSlot>
    <Start>2017-08-16T12:00:00+02:00</Start>
    <End>2017-08-16T13:00:00+02:00</End>
  </TimeSlot>
  <TimeSlot>
    <Start>2017-08-16T13:00:00+02:00</Start>
    <End>2017-08-16T14:00:00+02:00</End>
  </TimeSlot>
  <TimeSlot>
    <Start>2017-08-16T14:00:00+02:00</Start>
    <End>2017-08-16T15:00:00+02:00</End>
  </TimeSlot>
  <TimeSlot>
    <Start>2017-08-16T15:00:00+02:00</Start>
    <End>2017-08-16T16:00:00+02:00</End>
  </TimeSlot>
  <TimeSlot>
    <Start>2017-08-16T16:00:00+02:00</Start>
    <End>2017-08-16T17:00:00+02:00</End>
  </TimeSlot>
</DeliveryWindow>"""


def test_get_delivery_window():

    @urlmatch(path=r'/services/rest/inbounds/delivery-windows$')
    def delivery_window_stub(url, request):
        return DELIVERY_WINDOW_RESPONSE

    with HTTMock(delivery_window_stub):
        api = PlazaAPI('api_key', 'api_secret', test=True)

        param_date = '30-01-2017'

        with pytest.raises(TypeError):
            delivery_window = api.inbounds.getDeliveryWindow(
                delivery_date=param_date)

        with pytest.raises(TypeError):
            delivery_window = api.inbounds.getDeliveryWindow(
                items_to_send=20)

        delivery_window = api.inbounds.getDeliveryWindow(
            delivery_date=param_date, items_to_send=20)

        time_slot_0 = delivery_window[0]
        assert isinstance(time_slot_0.Start, datetime)
        assert isinstance(time_slot_0.End, datetime)


# original orderId is 4012345678
RI_str_1 = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ReturnItems xmlns="https://plazaapi.bol.com/services/xsd/v2/plazaapi.xsd">
 <Item>
   <ReturnNumber>31234567</ReturnNumber>
    <OrderId>4123456789</OrderId>
    <ShipmentId>0</ShipmentId>
    <EAN>9781781103524</EAN>
    <Title>Harry Potter en de Relieken van de Dood</Title>
    <Quantity>1</Quantity>
    <ReturnDateAnnouncement>2016-11-14+01:00</ReturnDateAnnouncement>
    <ReturnReason>Niet naar verwachting</ReturnReason>
    <CustomerDetails>
       <SalutationCode>02</SalutationCode>
       <FirstName>Jane</FirstName>
       <Surname>Doe</Surname>
       <Streetname>Mainstreet</Streetname>
       <Housenumber>77</Housenumber>
       <HousenumberExtended>BIS</HousenumberExtended>
       <ZipCode>1234 AA</ZipCode>
       <City>AMSTERDAM</City>
       <CountryCode>NL</CountryCode>
       <Email>example@example.com</Email>
       <DeliveryPhoneNumber>0612345678</DeliveryPhoneNumber>
       <Company>ACME</Company>
    </CustomerDetails>
 </Item>
</ReturnItems>"""

RI_str_2 = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ReturnItems xmlns="https://plazaapi.bol.com/services/xsd/v2/plazaapi.xsd">
 <Item>
   <ReturnNumber>31234568</ReturnNumber>
    <OrderId>4123456790</OrderId>
    <ShipmentId>0</ShipmentId>
    <EAN>9781781103524</EAN>
    <Title>Harry Potter en de Relieken van de Dood</Title>
    <Quantity>1</Quantity>
    <ReturnDateAnnouncement>2016-11-14+01:00</ReturnDateAnnouncement>
    <ReturnReason>Niet naar verwachting</ReturnReason>
    <CustomerDetails>
       <SalutationCode>02</SalutationCode>
       <FirstName>Jane</FirstName>
       <Surname>Doe</Surname>
       <Streetname>Mainstreet</Streetname>
       <Housenumber>77</Housenumber>
       <HousenumberExtended>BIS</HousenumberExtended>
       <ZipCode>1234 AA</ZipCode>
       <City>AMSTERDAM</City>
       <CountryCode>NL</CountryCode>
       <Email>example@example.com</Email>
       <DeliveryPhoneNumber>0612345678</DeliveryPhoneNumber>
       <Company>ACME</Company>
    </CustomerDetails>
 </Item>
</ReturnItems>"""

UNHANDLED_RETUERN_ITEMS_RESPONSE = [RI_str_1, RI_str_2]


def test_get_unhandled_return_items():

    return_no = 0

    @urlmatch(path=r'/services/rest/return-items/v2/unhandled')
    def unhandled_return_items_stub(url, request):
        return UNHANDLED_RETUERN_ITEMS_RESPONSE[return_no]

    with HTTMock(unhandled_return_items_stub):
        api = PlazaAPI('api_key', 'api_secret', test=True)

        unhandled_return_items_0 = api.return_items.getUnhandled()

        return_items_0 = unhandled_return_items_0[0]
        assert return_items_0.ReturnNumber, 31234567
        assert return_items_0.OrderId == 4123456789
        assert return_items_0.ShipmentId == 0
        assert return_items_0.EAN == '9781781103524'
        return_items_0_customer = return_items_0.CustomerDetails
        assert return_items_0_customer.FirstName == "Jane"
        assert return_items_0_customer.Surname == "Doe"
        assert return_items_0_customer.ZipCode == "1234 AA"


RI_handle_str_1 = """<?xml version="1.0" encoding="UTF-8"?>
<ns1:ProcessStatus
xmlns:ns1="https://plazaapi.bol.com/services/xsd/v2/plazaapi.xsd">
   <ns1:id>112748417</ns1:id>
   <ns1:sellerId>999849</ns1:sellerId>
   <ns1:entityId>65380525</ns1:entityId>
   <ns1:eventType>HANDLE_RETURN_ITEM</ns1:eventType>
   <ns1:description>Handle the return item with returnNumber 65380525
</ns1:description>
   <ns1:status>PENDING</ns1:status>
   <ns1:createTimestamp>2019-02-19T09:08:36.629+01:00</ns1:createTimestamp>
   <ns1:Links>
      <ns1:link
ns1:rel="self"
ns1:href="https://plazaapi.bol.com/services/rest/process-status/v2/112748417"
ns1:method="GET" />
   </ns1:Links>
</ns1:ProcessStatus>"""

HANDLE_RETURN_ITEMS_RESPONSE = [RI_handle_str_1]


def test_handle_return_items():

    return_no = 0

    @urlmatch(path=r'/services/rest/return-items/v2/65380525/handle$')
    def handle_return_items_stub(url, request):
        return HANDLE_RETURN_ITEMS_RESPONSE[return_no]

    with HTTMock(handle_return_items_stub):
        api = PlazaAPI('api_key', 'api_secret', test=True)

        handle_return_item_process = api.return_items.handleReturnItem(
            65380525,
            'FAILS_TO_MATCH_RETURN_CONDITIONS',
            2)

        assert handle_return_item_process.id, 112748417
        assert handle_return_item_process.eventType == 'HANDLE_RETURN_ITEM'
        assert handle_return_item_process.status == 'PENDING'
