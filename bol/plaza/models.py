from decimal import Decimal
import dateutil.parser


class Field(object):

    def parse(self, api, xml, instance):
        raise NotImplementedError


class TextField(Field):

    def parse(self, api, xml, instance):
        return xml.text


class BooleanField(Field):

    def parse(self, api, xml, instance):
        return xml.text == 'true'


class DecimalField(Field):

    def parse(self, api, xml, instance):
        return Decimal(xml.text)


class DateTimeField(Field):

    def parse(self, api, xml, instance):
        # WORKAROUND: At least on the test API I am bumping into this kind of
        # data: '2016-09-19+02:00'. Here, the time seems missing, only the
        # timezone offset is present. Let's detect this and handle gracefully.
        # Contacted BOL, awaiting reply...
        text = xml.text
        if text[10] == '+':
            text = text[:10] + 'T00:00:00' + text[10:]
        # (end WORKAROUND)
        return dateutil.parser.parse(text)


class IntegerField(Field):

    def parse(self, api, xml, instance):
        return int(xml.text)


class ModelField(Field):

    def __init__(self, model):
        self.model = model

    def parse(self, api, xml, instance):
        return self.model.parse(api, xml)


class Model(object):

    @classmethod
    def parse(cls, api, xml):
        m = cls()
        m.xml = xml
        for element in xml.getchildren():
            if '}' in element.tag:
                tag = element.tag.partition('}')[2]
            elif ':' in element.tag:
                tag = element.tag.partition(':')[2]
            else:
                tag = element.tag
            field = getattr(m.Meta, tag, TextField())
            setattr(m, tag, field.parse(api, element, m))
        return m


class ModelList(list, Model):

    @classmethod
    def parse(cls, api, xml):
        ml = cls()
        ml.xml = xml
        item_tag = getattr(ml.Meta, 'item_type_tag', None)
        for element in xml.getchildren():
            if item_tag and item_tag != element.tag:
                continue
            ml.append(ml.Meta.item_type.parse(api, element))
        return ml


class CustomerDetailsBase(Model):

    class Meta:
        SalutationCode = IntegerField()
        Surname = TextField()
        Streetname = TextField()
        Housenumber = IntegerField()
        HousenumberExtended = TextField()
        ZipCode = TextField()
        City = TextField()
        CountryCode = TextField()
        Email = TextField()
        Company = TextField()


class BillingDetails(CustomerDetailsBase):

    class Meta(CustomerDetailsBase.Meta):
        Firstname = TextField()


class ShipmentDetails(Model):

    class Meta(CustomerDetailsBase.Meta):
        Firstname = TextField()


class CustomerDetails(Model):

    class Meta:
        ShipmentDetails = ModelField(ShipmentDetails)
        BillingDetails = ModelField(BillingDetails)


class Invoice(Model):

    class Meta:
        pass


class InvoiceListItem(Model):

    class Meta:
        pass


class Invoices(ModelList):

    class Meta:
        item_type = InvoiceListItem
        item_type_tag = 'InvoiceListItem'


class Price(Model):

    class Meta:
        PriceAmount = DecimalField()
        BaseQuantity = DecimalField()


class InvoiceSpecificationItem(Model):

    class Meta:
        Price = ModelField(Price)


class InvoiceSpecification(Model):

    class Meta:
        Item = ModelField(InvoiceSpecificationItem)
        pass


class InvoiceSpecifications(ModelList):

    class Meta:
        item_type = InvoiceSpecification


class OrderItem(Model):

    class Meta:
        OfferPrice = DecimalField()
        TransactionFee = DecimalField()
        Quantity = IntegerField()


class OrderItems(ModelList):

    class Meta:
        item_type = OrderItem


class Order(Model):

    class Meta:
        CustomerDetails = ModelField(CustomerDetails)
        OrderItems = ModelField(OrderItems)
        DateTimeCustomer = DateTimeField()
        DateTimeDropShipper = DateTimeField()


class Orders(ModelList):

    class Meta:
        item_type = Order


class ShipmentItem(Model):

    class Meta:
        OrderItem = ModelField(OrderItem)


class ShipmentItems(ModelList):

    class Meta:
        item_type = ShipmentItem


class Transport(Model):

    class Meta:
        pass


class Shipment(Model):

    class Meta:
        ShipmentDate = DateTimeField()
        ExpectedDeliveryDate = DateTimeField()
        ShipmentItems = ModelField(ShipmentItems)
        Transport = ModelField(Transport)


class Shipments(ModelList):

    class Meta:
        item_type = Shipment


class Labels(Model):

    class Meta:
        TransporterCode = TextField()
        LabelType = TextField()
        MaxWeight = TextField()
        MaxDimensions = TextField()
        RetailPrice = DecimalField()
        PurchasePrice = DecimalField()
        Discount = DecimalField()
        ShippingLabelCode = TextField()


class PurchasableShippingLabels(ModelList):

    class Meta:
        item_type = Labels


class RI_CustomerDetails(CustomerDetailsBase):

    class Meta(CustomerDetailsBase.Meta):
        FirstName = TextField()
        DeliveryPhoneNumber = IntegerField()


class Item(Model):

    class Meta:
        ReturnNumber = IntegerField()
        OrderId = IntegerField()
        ShipmentId = IntegerField()
        EAN = TextField()
        Title = TextField()
        Quantity = TextField()
        ReturnDateAnnouncement = TextField()
        ReturnReason = TextField()
        CustomerDetails = ModelField(RI_CustomerDetails)


class ReturnItems(ModelList):

    class Meta:
        item_type = Item


class ReturnItemStatusUpdate(Model):

    class Meta:
        StatusReason = TextField()
        QuantityReturned = IntegerField()


class ProcessStatusLinks(Model):

    class Meta:
        link = IntegerField()


class ProcessStatus(Model):

    class Meta:
        id = IntegerField()
        sellerId = IntegerField()
        entityId = IntegerField()
        eventType = TextField()
        status = TextField()
        createTimestamp = TextField()
        ReturnDateAnnouncement = TextField()
        ReturnReason = TextField()
        item_type = ProcessStatusLinks()

# models used for 'get single offer' method  ::
# RetailerOfferStatus, RetailerOffer, RetailerOffers, OffersResponse


class RetailerOfferStatus(Model):

    class Meta:
        Published = BooleanField()
        ErrorCode = TextField()
        ErrorMessage = TextField()


class RetailerOffer(Model):

    class Meta:
        EAN = TextField()
        Condition = TextField()
        Price = DecimalField()
        DeliveryCode = TextField()
        QuantityInStock = DecimalField()
        UnreservedStock = DecimalField()
        Publish = BooleanField()
        ReferenceCode = TextField()
        Description = TextField()
        Title = TextField()
        FulfillmentMethod = TextField()
        item_type = RetailerOfferStatus()


class RetailerOffers(ModelList):

    class Meta:
        item_type = RetailerOffer()


class OffersResponse(ModelList):

    class Meta:
        item_type = RetailerOffers()


# models used for 'OffersExport' method  :: OfferFileUrl, OfferFile
class OfferFileUrl(Model):

    class Meta:
        Url = TextField()


class OfferFile(Model):

    class Meta:
        item_type = OfferFileUrl()


# models used for 'Delete' method  ::
# DeleteBulkRequest, RetailerOfferIdentifier
class RetailerOfferIdentifier(Model):

    class Meta:
        EAN = TextField()
        Condition = TextField()


class DeleteBulkRequest(ModelList):

    class Meta:
        item_type = RetailerOfferIdentifier()


# models used for 'GetAllInbounds' method for fbb-endpoints ::
# GetAllInbounds, GetAllInbound, TimeSlot, FbbTransporter
class FbbTransporter(Model):

    class Meta:
        Name = TextField()
        Code = TextField()


class TimeSlot(Model):

    class Meta:
        Start = DateTimeField()
        End = DateTimeField()


class GetAllInbound(Model):

    class Meta:
        ID = IntegerField()
        Reference = TextField()
        CreationDate = DateTimeField()
        State = TextField()
        LabellingService = BooleanField()
        AnnouncedBSKUs = IntegerField()
        AnnouncedQuantity = IntegerField()
        ReceivedBSKUs = IntegerField()
        ReceivedQuantity = IntegerField()
        TimeSlot = ModelField(TimeSlot)
        FbbTransporter = ModelField(FbbTransporter)


class GetAllInboundList(ModelList):

    class Meta:
        item_type = GetAllInbound


class GetAllInbounds(Model):

    class Meta:
        TotalCount = IntegerField()
        TotalPageCount = IntegerField()
        AllInbound = ModelField(GetAllInboundList)


# models used for 'GetSingleInbound' method for fbb-endpoints ::
# GetAllInbounds, GetAllInbound, SingleBoundProducts, SingleBoundProduct,
# StateTransitions, StateTransition,
# existing classes: TimeSlot, FbbTransporter


class InboundState(Model):

    class Meta:
        State = TextField()
        StateDate = DateTimeField()


class StateTransitions(ModelList):

    class Meta:
        item_type = InboundState()


class SingleBoundProduct(Model):

    class Meta:
        EAN = TextField()
        State = TextField()
        BSKUs = TextField()
        AnnouncedQuantity = IntegerField()
        ReceivedQuantity = IntegerField()


class SingleBoundProducts(ModelList):

    class Meta:
        item_type = SingleBoundProduct()


class GetSingleInbound(GetAllInbound):

    class Meta(GetAllInbound.Meta):
        Products = ModelField(SingleBoundProducts)
        StateTransitions = ModelField(StateTransitions)


# models used for 'Get Inventory' method for fbb-endpoints ::
# InventoryResponse, InventoryOffers, InventoryOffer
class InventoryOffer(Model):

    class Meta:
        EAN = TextField()
        BSKU = TextField()
        Title = TextField()
        Stock = IntegerField()
        # NCK_Stock = IntegerField()


class InventoryOffers(ModelList):

    class Meta:
        item_type = InventoryOffer


class InventoryResponse(Model):

    class Meta:
        TotalCount = IntegerField()
        TotalPageCount = IntegerField()
        Offers = ModelField(InventoryOffers)


# models used for 'Get Delivery Window' method for fbb-endpoints ::
# DeliveryWindowResponse
class DeliveryWindowResponse(ModelList):

    class Meta:
        item_type = TimeSlot
