import time
import requests
import hmac
import hashlib
import base64
from datetime import datetime
from datetime import date
import collections
from enum import Enum

import traceback


from xml.etree import ElementTree

from .models import (
    Orders, Shipments, ProcessStatus, Invoices, Invoice,
    InvoiceSpecifications)

# custom Method Models For DreamBits
from .models import PurchasableShippingLabels, ReturnItems
from .models import OffersResponse, OfferFile  # DeleteBulkRequest

# for get Inventory method
from .models import InventoryResponse

# for Get All Bounds method
from .models import GetAllInbounds

# for Get Single Bounds method
from .models import GetSingleInbound

# for Get Delivery Window method
from .models import DeliveryWindowResponse


__all__ = ['PlazaAPI']

PLAZA_API_V1 = "https://plazaapi.bol.com/services/xsd/v1/plazaapi.xsd"


def type_exception(_type, _var):
    raise TypeError("Required {0}, found-> {1} ".format(_type, type(_var)))


def key_exception(_var):
    raise KeyError("Required {0} not found".format(_var))


class TransporterCode(Enum):
    """
    https://developers.bol.com/documentatie/plaza-api/developer-guide-plaza-api/appendix-a-transporters/
    """
    DHLFORYOU = 'DHLFORYOU'
    UPS = 'UPS'
    TNT = 'TNT'
    TNT_EXTRA = 'TNT-EXTRA'
    TNT_BRIEF = 'TNT_BRIEF'
    TNT_EXPRESS = 'TNT-EXPRESS'
    COURIER = 'COURIER'
    DYL = 'DYL'
    DPD_NL = 'DPD-NL'
    DPD_BE = 'DPD-BE'
    BPOST_BE = 'BPOST_BE'
    BPOST_BRIEF = 'BPOST_BRIEF'
    BRIEFPOST = 'BRIEFPOST'
    GLS = 'GLS'
    FEDEX_NL = 'FEDEX_NL'
    FEDEX_BE = 'FEDEX_BE'
    OTHER = 'OTHER'
    DHL = 'DHL'
    DHL_DE = 'DHL_DE'
    DHL_GLOBAL_MAIL = 'DHL-GLOBAL-MAIL'
    TSN = 'TSN'
    FIEGE = 'FIEGE'
    TRANSMISSION = 'TRANSMISSION'
    PARCEL_NL = 'PARCEL-NL'
    LOGOIX = 'LOGOIX'
    PACKS = 'PACKS'
    RJP = 'RJP'

    @classmethod
    def to_string(cls, transporter_code):
        if isinstance(transporter_code, TransporterCode):
            transporter_code = transporter_code.value
        assert transporter_code in map(
            lambda c: c.value, list(TransporterCode))
        return transporter_code


class MethodGroup(object):

    def __init__(self, api, group):
        self.api = api
        self.group = group

    def request(self, method, path='', params={}, data=None,
                accept="application/xml"):
        uri = '/services/rest/{group}/{version}{path}'.format(
            group=self.group,
            version=self.api.version,
            path=path)
        xml = self.api.request(method, uri, params=params, data=data,
                               accept=accept)
        return xml

    def request_inbound(self, method, path='', params={}, data=None,
                        accept="application/xml"):
        uri = '/services/rest/{group}/{path}'.format(
            group=self.group,
            path=path)
        xml = self.api.request(method, uri, params=params, data=data,
                               accept=accept)
        return xml

    def create_request_xml(self, root, **kwargs):
        elements = self._create_request_xml_elements(1, **kwargs)
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<{root} xmlns="https://plazaapi.bol.com/services/xsd/v2/plazaapi.xsd">
{elements}
</{root}>
""".format(root=root, elements=elements)
        return xml

    def create_request_offers_xml(self, root, **kwargs):
        elements = self._create_request_xml_elements(1, **kwargs)
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<{root} xmlns="https://plazaapi.bol.com/offers/xsd/api-2.0.xsd">
{elements}
</{root}>
""".format(root=root, elements=elements)
        return xml

    def create_request_inbound_xml(self, root, **kwargs):
        elements = self.create_request_xml_elements_for_create_inbound(
            1, **kwargs)
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<{root} xmlns="https://plazaapi.bol.com/services/xsd/v1/plazaapi.xsd">
{elements}
</{root}>
""".format(root=root, elements=elements)
        return xml

    def create_request_xml_elements_for_create_inbound(self, indent, **kwargs):
        '''
        this function was copied from #_create_request_ixml_elements
        to maintain proper structure for specially #create_request_inbound_xml
        '''
        # sort to make output deterministic
        kwargs = collections.OrderedDict(sorted(kwargs.items()))
        xml = ''
        for tag, value in list(kwargs.items()):
            if value is not None:
                prefix = ' ' * 4 * indent
                if not isinstance(value, list):
                    if isinstance(value, dict):
                        text = '\n{}\n{}'.format(
                            self._create_request_xml_elements(
                                indent + 1, **value),
                            prefix)
                    elif isinstance(value, datetime):
                        text = value.isoformat()
                    else:
                        text = str(value)
                    # TODO: Escape! For now this will do I am only dealing
                    # with track & trace codes and simplistic IDs...
                    if xml:
                        xml += '\n'
                    xml += prefix
                    xml += "<{tag}>{text}</{tag}>".format(
                        tag=tag,
                        text=text
                    )
                else:
                    text = ''
                    for item in value:
                        if isinstance(item, dict):
                            text += '\n{}\n{}'.format(
                                self._create_request_xml_elements(
                                    indent + 1, **item),
                                prefix)
                        else:
                            text += str(item)
                        # TODO: Escape! For now this will do I am only dealing
                        # with track & trace codes and simplistic IDs...
                    if xml:
                        xml += '\n'
                    xml += prefix
                    xml += "<{tag}>{text}</{tag}>".format(
                        tag=tag,
                        text=text
                    )
        return xml

    def _create_request_xml_elements(self, indent, **kwargs):
        '''
        The original one, ... change it at your own risk ...  :)
        '''
        # sort to make output deterministic
        kwargs = collections.OrderedDict(sorted(kwargs.items()))
        xml = ''
        for tag, value in list(kwargs.items()):
            if value is not None:
                prefix = ' ' * 4 * indent
                if not isinstance(value, list):
                    if isinstance(value, dict):
                        text = '\n{}\n{}'.format(
                            self._create_request_xml_elements(
                                indent + 1, **value),
                            prefix)
                    elif isinstance(value, datetime):
                        text = value.isoformat()
                    else:
                        text = str(value)
                    # TODO: Escape! For now this will do I am only dealing
                    # with track & trace codes and simplistic IDs...
                    if xml:
                        xml += '\n'
                    xml += prefix
                    xml += "<{tag}>{text}</{tag}>".format(
                        tag=tag,
                        text=text
                    )
                else:
                    for item in value:
                        if isinstance(item, dict):
                            text = '\n{}\n{}'.format(
                                self._create_request_xml_elements(
                                    indent + 1, **item),
                                prefix)
                        else:
                            text = str(item)
                        # TODO: Escape! For now this will do I am only dealing
                        # with track & trace codes and simplistic IDs...
                        if xml:
                            xml += '\n'
                        xml += prefix
                        xml += "<{tag}>{text}</{tag}>".format(
                            tag=tag,
                            text=text
                        )
        return xml


class OrderMethods(MethodGroup):

    def __init__(self, api):
        super(OrderMethods, self).__init__(api, 'orders')

    def list(self, page=None, fulfilment_method=None,
             accept="application/xml"):
        params = {}

        if page:
            params['page'] = page

        if fulfilment_method:
            params['fulfilment-method'] = fulfilment_method

        xml = self.request('GET', params=params,
                           accept="application/vnd.orders-v2.1+xml")
        return Orders.parse(self.api, xml)


class InvoiceMethods(MethodGroup):

    def __init__(self, api):
        super(InvoiceMethods, self).__init__(api, 'invoices')

    def list(self, order_id=None, period_from=None, period_to=None):
        params = {}
        if order_id:
            params['orderId'] = order_id
        if period_from or period_to:
            if (not isinstance(period_from, date) or
                    not isinstance(period_to, date)):
                raise ValueError()
            params['period'] = '/'.join([
                period_from.isoformat(),
                period_to.isoformat()
            ])
        xml = self.request('GET', '/services/rest/invoices', params=params)
        return Invoices.parse(self.api, xml)

    def get(self, invoice_id):
        xml = self.request('GET', '/services/rest/invoices/{}'.format(
            invoice_id))
        return Invoice.parse(self.api, xml)

    def get_specification(self, invoice_id, page=None):
        params = {}
        if page is not None:
            params['page'] = page
        xml = self.request(
            'GET',
            '/services/rest/invoices/{}/specification'.format(
                invoice_id),
            params=params)
        return InvoiceSpecifications.parse(self.api, xml)


class ProcessStatusMethods(MethodGroup):

    def __init__(self, api):
        super(ProcessStatusMethods, self).__init__(api, 'process-status')

    def get(self, id):
        xml = self.request('GET', '/{}'.format(id))
        return ProcessStatus.parse(self.api, xml)


class ShipmentMethods(MethodGroup):

    def __init__(self, api):
        super(ShipmentMethods, self).__init__(api, 'shipments')

    def list(self, page=None, fulfilment_method=None, order_id=None,
             accept="application/xml"):
        params = {}

        if page:
            params['page'] = page

        if order_id:
            params['order-id'] = order_id

        if fulfilment_method:
            params['fulfilment-method'] = fulfilment_method

        xml = self.request('GET', params=params,
                           accept="application/vnd.shipments-v2.1+xml")
        return Shipments.parse(self.api, xml)

    def create(self, order_item_id, date_time, expected_delivery_date,
               shipment_reference=None, transporter_code=None,
               track_and_trace=None, shipping_label_code=None):
        # Moved the params to a dict so it can be easy to add/remove parameters
        values = {
            'OrderItemId': order_item_id,
            'DateTime': date_time,
            'ShipmentReference': shipment_reference,
            'ExpectedDeliveryDate': expected_delivery_date,
        }

        if transporter_code:
            transporter_code = TransporterCode.to_string(
                transporter_code)

        if shipping_label_code:
            values['ShippingLabelCode'] = shipping_label_code
        else:
            values['Transport'] = {
                'TransporterCode': transporter_code,
                'TrackAndTrace': track_and_trace
            }

        xml = self.create_request_xml(
            'ShipmentRequest',
            **values)

        response = self.request('POST', data=xml)
        return ProcessStatus.parse(self.api, response)


class TransportMethods(MethodGroup):

    def __init__(self, api):
        super(TransportMethods, self).__init__(api, 'transports')

    def update(self, id, transporter_code, track_and_trace):
        transporter_code = TransporterCode.to_string(transporter_code)
        xml = self.create_request_xml(
            'ChangeTransportRequest',
            TransporterCode=transporter_code,
            TrackAndTrace=track_and_trace)
        response = self.request('PUT', '/{}'.format(id), data=xml)
        return ProcessStatus.parse(self.api, response)

    def getSingle(self, transportId, shippingLabelId, file_location):
        content = self.request('GET', '/{}/shipping-label/{}'.format(
            transportId,
            shippingLabelId),
            params={}, data=None, accept="application/pdf")
        # Now lets store this content in pdf:

        with open(file_location, 'wb') as f:
            f.write(content)


class PurchasableShippingLabelsMethods(MethodGroup):

    def __init__(self, api):
        super(PurchasableShippingLabelsMethods, self).__init__(
            api,
            'purchasable-shipping-labels')

    def get(self, id):
        params = {'orderItemId': id}
        xml = self.request('GET', params=params)
        return PurchasableShippingLabels.parse(self.api, xml)


class ReturnItemsMethods(MethodGroup):

    def __init__(self, api):
        super(ReturnItemsMethods, self).__init__(api, 'return-items')

    def getUnhandled(self):
        xml = self.request('GET', path="/unhandled", accept="application/xml")
        return ReturnItems.parse(self.api, xml)

    def handleReturnItem(self, return_no, status_reason, qty, params={}):
        xml = self.create_request_xml(
            'ReturnItemStatusUpdate',
            StatusReason=status_reason,
            QuantityReturned=qty
            )
        uri = '/services/rest/{group}/{version}{path}'.format(
            group=self.group,
            version=self.api.version,
            path='/{}/handle'.format(return_no))
        response = self.api.request('PUT', uri, params=params,
                                    data=xml, accept="application/xml")
        return ProcessStatus.parse(self.api, response)


class OffersMethods(MethodGroup):

    def __init__(self, api):
        super(OffersMethods, self).__init__(api, 'offers')

    def upsertOffers(self, offers, path='/', params={},
                     data=None, accept="application/xml"):
        xml = self.create_request_offers_xml(
            'UpsertRequest',
            RetailerOffer=offers)
        uri = '/{group}/{version}{path}'.format(
            group=self.group,
            version=self.api.version,
            path=path)
        response = self.api.request('PUT', uri, params=params,
                                    data=xml, accept=accept)
        # return ProcessStatus.parse(self.api, xml)
        if response is True:
            return response
        # else:
        #     return UpsertOffersError.parse(self.api, response)

    def getSingleOffer(self, ean, path='/', params={},
                       data=None, accept="application/xml"):

        uri = '/{group}/{version}{path}'.format(
            group=self.group,
            version=self.api.version,
            path='/{}'.format(ean))
        response = self.api.request('GET', uri, params=params,
                                    data=data, accept=accept)
        return OffersResponse.parse(self.api, response)

    def getOffersFileName(self, path='/', params={},
                          data=None, accept="application/xml"):

        uri = '/{group}/{version}{path}'.format(
            group=self.group,
            version=self.api.version,
            path='/export/')
        response = self.api.request('GET', uri, params=params,
                                    data=data, accept=accept)
        return OfferFile.parse(self.api, response)

    def getOffersFile(self, csv, path='/', params={},
                      data=None, accept="text/csv"):
        csv_path = csv.split("/v2/")
        uri = '/{group}/{version}{path}'.format(
            group=self.group,
            version=self.api.version,
            path='/{}'.format(csv_path[1]))
        response = self.api.request('GET', uri, params=params,
                                    data=data, accept=accept)
        return response

    def deleteOffers(self, offers, path='/', params={},
                     data=None, accept="application/xml"):
        try:
            xml = self.create_request_offers_xml(
                'DeleteBulkRequest',
                RetailerOfferIdentifier=offers[0])
            uri = '/{group}/{version}{path}'.format(
                group=self.group,
                version=self.api.version,
                path=path)
            response = self.api.request("DELETE", uri, params=params,
                                        data=xml, accept=accept)
            if response is True:
                return response
        except Exception:
            print("Got into Exception \n{0}".format(traceback.print_exc()))


class InboundMethods(MethodGroup):

    def __init__(self, api):
        super(InboundMethods, self).__init__(api, 'inbounds')

    def getAllInbounds(self, page=None):
        uri = '/services/rest/{group}'.format(
            group=self.group)
        all_inbound = self.api.request('GET', uri)

        # need to handle the structure after modifying xml data
        # as the data is not structured properly

        ElementTree.register_namespace('', PLAZA_API_V1)

        allit = list(all_inbound)

        inbounds = [x for x in all_inbound.iter()
                    if x.tag.partition('}')[2] == 'Inbound']

        for x in inbounds:
            all_inbound.remove(x)

        newinbound = ElementTree.Element('{'+PLAZA_API_V1+'}AllInbound')
        # This is hacky solution to add proper namespace.
        # This needs to be checked properly but
        # only it has been tested against
        # real data

        for x in inbounds:
            newinbound.append(x)

        all_inbound.append(newinbound)

        return GetAllInbounds.parse(self.api, all_inbound)

    def getSingleInbound(self, inbound_id=None):

        if not isinstance(inbound_id, int):
            type_exception('int', inbound_id)

        response = self.request_inbound('GET', path=inbound_id)
        return GetSingleInbound.parse(self.api, response)

    def create(self, reference=None, time_slot=None, fbb_transporter=None,
               labelling_service=None, prod_dict=None):
        # Moved the params to a dict
        # so it can be easy to add/remove parameters
        values = {
            'Reference': reference,
            'LabellingService': labelling_service,
        }

        if 'Start' in time_slot and 'End' in time_slot:
            if not isinstance(time_slot['Start'], str):
                type_exception('str', time_slot['Start'])
            if not isinstance(time_slot['End'], str):
                type_exception('str', time_slot['End'])
            values['TimeSlot'] = time_slot

        if 'Code' in time_slot and 'Name' in time_slot:
            if 'Code' not in fbb_transporter:
                key_exception('Code')
            if not isinstance(fbb_transporter['Code'], str):
                type_exception('str', fbb_transporter['Code'])

            if 'Name' not in fbb_transporter:
                key_exception('Name')
            if not isinstance(fbb_transporter['Name'], str):
                type_exception('str', fbb_transporter['Name'])
        values['FbbTransporter'] = fbb_transporter

        values['Products'] = []
        if isinstance(prod_dict, list):
            for prod in prod_dict:
                if isinstance(prod, dict):
                    self.check_prod(prod)
                values['Products'].append(prod)

        xml = self.create_request_inbound_xml('InboundRequest', **values)

        response = self.request_inbound('POST', data=xml)
        return ProcessStatus.parse(self.api, response)

    def check_prod(self, prod):
        if 'Product' not in prod:
            key_exception('Product')

        if not isinstance(prod['Product'], dict):
            type_exception('dict', prod['Product'])

        prod_keys = list(prod['Product'].keys())
        if 'EAN' not in prod_keys:
            key_exception('EAN')
        if 'AnnouncedQuantity' not in prod_keys:
            key_exception('AnnouncedQuantity')

        if not isinstance(prod['Product']['EAN'], int):
            type_exception('int', prod['Product']['EAN'])
        if not isinstance(prod['Product']['AnnouncedQuantity'], float):
            type_exception('float', prod['Product']['AnnouncedQuantity'])

    def getDeliveryWindow(self, delivery_date=None, items_to_send=None):
        params = {}

        if not isinstance(delivery_date, str):
            type_exception('str', delivery_date)
        params['delivery-date'] = delivery_date

        if not isinstance(items_to_send, int):
            type_exception('int', items_to_send)
        params['items-to-send'] = items_to_send

        response = self.request_inbound('GET', path='delivery-windows',
                                        params=params)

        return DeliveryWindowResponse.parse(self.api, response)

    def getShippingLabel(self, inbound_id=None):
        '''
        This method returns pdf data of shipping label for given inbound
        '''

        if not isinstance(inbound_id, int):
            type_exception('int', inbound_id)

        response = self.request_inbound('GET',
                                        path='{0}/shippinglabel'.format(
                                            inbound_id),
                                        accept="application/pdf")

        return response

    def getPackingListDetails(self, inbound_id=None):
        '''
        This method returns pdf data of packing list details for given inbound
        '''

        if not isinstance(inbound_id, int):
            type_exception('int', inbound_id)

        response = self.request_inbound('GET',
                                        path='{0}/packinglistdetails'.format(
                                            inbound_id),
                                        accept="application/pdf")

        return response


class InventoryMethods(MethodGroup):

    def __init__(self, api):
        super(InventoryMethods, self).__init__(api, 'inventory')

    def getInventory(self, page=None, quantity=None, stock=None, state=None,
                     query=None):
        params = {}

        if page:
            if not isinstance(page, int):
                type_exception('int', page)
            params['page'] = page

        if quantity:
            params['quantity'] = quantity

        if stock:
            params['stock'] = stock

        if state:
            params['state'] = state

        if query:
            params['query'] = query

        uri = '/services/rest/{group}'.format(group=self.group)
        response = self.api.request('GET', uri, params=params, data=None)
        return InventoryResponse.parse(self.api, response)


class PlazaAPI(object):

    def __init__(self, public_key, private_key, test=False, timeout=None,
                 session=None):

        self.public_key = public_key
        self.private_key = private_key
        self.url = 'https://%splazaapi.bol.com' % ('test-' if test else '')

        self.version = 'v2'
        self.timeout = timeout
        self.orders = OrderMethods(self)
        self.invoices = InvoiceMethods(self)
        self.shipments = ShipmentMethods(self)
        self.process_status = ProcessStatusMethods(self)
        self.transports = TransportMethods(self)
        self.labels = PurchasableShippingLabelsMethods(self)
        self.session = session or requests.Session()
        self.return_items = ReturnItemsMethods(self)
        self.offers = OffersMethods(self)
        self.inbounds = InboundMethods(self)
        self.inventory = InventoryMethods(self)

    def request(self, method, uri, params={},
                data=None, accept="application/xml"):
        try:
            content_type = 'application/xml; charset=UTF-8'
            date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
            msg = """{method}

{content_type}
{date}
x-bol-date:{date}
{uri}""".format(content_type=content_type,
                date=date,
                method=method,
                uri=uri)
            h = hmac.new(
                self.private_key.encode('utf-8'),
                msg.encode('utf-8'), hashlib.sha256)
            b64 = base64.b64encode(h.digest())

            signature = self.public_key.encode('utf-8') + b':' + b64

            headers = {'Content-Type': content_type,
                       'X-BOL-Date': date,
                       'X-BOL-Authorization': signature,
                       'accept': accept}
            request_kwargs = {
                'method': method,
                'url': self.url + uri,
                'params': params,
                'headers': headers,
                'timeout': self.timeout,
            }
            if data:
                request_kwargs['data'] = data

            resp = self.session.request(**request_kwargs)

            resp_content = resp.content
            resp_text = resp.text

            if isinstance(resp_content, bytes):
                resp_content = resp_content.decode(encoding='utf-8')
            if isinstance(resp_text, bytes):
                resp_text = resp_text.decode(encoding='utf-8')

            if request_kwargs['url'] == 'https://plazaapi.bol.com/offers/v2/':
                if resp.status_code == 202 and resp_text is not None:
                    return True
                else:
                    tree = ElementTree.fromstring(resp_content)
                    return tree

            if 'https://plazaapi.bol.com/offers/v2/export/' in request_kwargs[
                    'url']:
                if accept == "text/csv":
                    return resp_text

            resp.raise_for_status()

            if accept == "application/pdf":
                return resp_content
            else:
                tree = ElementTree.fromstring(resp_content)
                return tree
        except Exception:
            print("Got into Exception \n{0}".format(traceback.print_exc()))
            return False
