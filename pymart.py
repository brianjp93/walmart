'''
wrapper around the walmart api

Walmart's API documentation -> https://developer.walmart.com/#/apicenter/marketPlace
'''
import requests
from requests import Request, Session
import time
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from uuid import uuid4
from xml.etree import ElementTree as ET
import pytz
from datetime import datetime
import zipfile
try:
    # python 2
    from StringIO import StringIO
except:
    # python 3
    from IO import StringIO


__author__ = 'Brian Perrett'
__date__   = 'Feb 10, 2017'


def clean_report(data_string):
    '''
    returns a string of the report
    '''
    f = zipfile.ZipFile(StringIO(data_string))
    filename = f.filelist[0].filename
    data = f.read(filename)
    return data


class Walmart():
    base_url = 'https://marketplace.walmartapis.com/'
    xml_head = '<?xml version="1.0" encoding="UTF-8"?>'
    def __init__(self, private_key, consumer_id, channel_type):
        self.private_key = private_key
        self.consumer_id = consumer_id
        self.channel_type = channel_type

    def get_headers(self, timestamp, signature):
        random_id = str(uuid4())
        headers = {
            'Accept': 'application/xml',
            'WM_SVC.NAME': 'Walmart Marketplace',
            'WM_CONSUMER.ID': '{}'.format(self.consumer_id),
            'WM_SEC.TIMESTAMP': str(timestamp),
            'WM_SEC.AUTH_SIGNATURE': signature,
            'WM_QOS.CORRELATION_ID': random_id,
            'WM_CONSUMER.CHANNEL.TYPE': self.channel_type,

            # walmart asks for this header but whenever I provide it my request is denied???
            # 'Host': 'https://marketplace.walmartapis.com'
            }
        return headers

    def sign(self, full_url, request_method):
        '''
        use the cryptography library to sign a specific string
        returns a tuple as (signature[string], timestamp[int in milliseconds])
        '''
        timestamp = str(int(time.time() * 1000))
        string_to_sign = '{consumer_id}\n{full_url}\n{http_method}\n{timestamp}\n'.format(**{
            'consumer_id': self.consumer_id,
            'full_url': full_url,
            'http_method': request_method.upper(),
            'timestamp': timestamp
            })
        pem_format = '-----BEGIN PRIVATE KEY-----\n{}\n-----END PRIVATE KEY-----'.format(self.private_key)
        crypto_key = serialization.load_pem_private_key(
            pem_format,
            password=None,
            backend=default_backend()
            )
        signature = crypto_key.sign(
            string_to_sign,
            padding.PKCS1v15(),
            hashes.SHA256()
            )
        signature = base64.b64encode(signature)
        return signature, timestamp

    ##############################################################
    ######################## ITEM METHODS ########################
    ##############################################################

    def get_item(self, sku):
        '''
        https://developer.walmartapis.com/#get-an-item
        '''
        full_url = '{}v2/items/{}'.format(self.base_url, sku)
        signature, timestamp = self.sign(full_url, 'GET')
        headers = self.get_headers(timestamp, signature)
        r = requests.get(full_url, headers=headers)
        return r

    def get_all_items(self, offset=0, limit=20):
        '''
        https://developer.walmartapis.com/#get-all-items

        '''
        full_url = '{}v2/items?sku=&limit={}&offset={}'.format(self.base_url, limit, offset)
        signature, timestamp = self.sign(full_url, 'GET')
        headers = self.get_headers(timestamp, signature)
        r = requests.get(full_url, headers=headers)
        return r

    def retire_item(self, sku):
        full_url = '{}v2/items/{}'.format(self.base_url, sku)
        signature, timestamp = self.sign(full_url, 'DELETE')
        headers = self.get_headers(timestamp, signature)
        r = requests.delete(full_url, headers=headers)
        return r

    ###########################################################
    ###################### PRICE METHODS ######################
    ###########################################################

    def update_price(self, sku, price, currency='USD'):
        '''
        '''
        full_url = '{}v2/prices?sku={}&currency={}&price={}'.format(self.base_url, sku, currency, price)
        signature, timestamp = self.sign(full_url, 'PUT')
        headers = self.get_headers(timestamp, signature)
        r = requests.put(full_url, headers=headers)
        return r

    def bulk_update_price(self, data=[], version='1.5', current_price_type_default='', currency_default='USD'):
        '''
        data is a list of dictionary objects which looks like...
            [{
                'sku':                  <sku>,
                'currency':             <currency>,
                'current_price':        <current_price>,
                'current_price_type':   <current_price_type>,
                'comparison_price':     <comparison_price>,
                ''
            }, ...]
        currenct_price_type -> ('BASE', 'CLEARANCE', 'REDUCED')
        '''
        full_url = '{}v3/feeds?feedType=price'.format(self.base_url)
        price_feed_elt = ET.Element('PriceFeed')
        price_feed_elt.set('xmlns:gmp', 'http://walmart.com/')
        price_header_elt = ET.SubElement(price_feed_elt, 'PriceHeader')
        version_elt = ET.SubElement(price_header_elt, 'version')
        version_elt.text = version
        for item in data:
            currency = str(item.get('currency', currency_default))
            price_elt = ET.SubElement(price_feed_elt, 'Price')
            item_identifier_elt = ET.SubElement(price_elt, 'itemIdentifier')
            sku_elt = ET.SubElement(item_identifier_elt, 'sku')
            sku_elt.text = item['sku']
            pricing_list_elt = ET.SubElement(price_elt, 'pricingList')
            pricing_elt = ET.SubElement(pricing_list_elt, 'pricing')
            current_price_elt = ET.SubElement(pricing_elt, 'currentPrice')
            current_price_value_elt = ET.SubElement(current_price_elt, 'value')
            current_price_value_elt.set('currency', currency)
            current_price_value_elt.set('amount', str(item['current_price']))
            current_price_type = item.get('current_price_type', current_price_type_default)
            if current_price_type:
                current_price_type_elt = ET.SubElement(pricing_elt, 'currentPriceType')
                current_price_type_elt.text = current_price_type
            if item.get('comparison_price', None):
                comparison_price_elt = ET.SubElement(pricing_elt, 'comparisonPrice')
                comparison_price_value_elt = ET.SubElement(comparison_price_elt, 'value')
                comparison_price_value_elt.set('currency', currency)
                comparison_price_value_elt.set('amount', str(item['comparison_price']))
        sig, ts = self.sign(full_url, 'POST')
        headers = self.get_headers(ts, sig)
        headers['Content-Type'] = 'multipart/form-data;'
        xml_string = self.xml_head + ET.tostring(price_feed_elt)
        files = {'file': ('pricing.xml', xml_string)}
        r = requests.post(full_url, headers=headers, files=files)
        return r

    ###########################################################
    ###################### ORDER METHODS ######################
    ###########################################################

    def get_order(self, order_id):
        '''
        order_id -> walmart purchase_order_id
        '''
        full_url = '{}v3/orders/{}'.format(self.base_url, order_id)
        signature, timestamp = self.sign(full_url, 'GET')
        headers = self.get_headers(timestamp, signature)
        r = requests.get(full_url, headers=headers)
        return r

    def get_all_released_orders(
            self,
            created_start_date=None,        # ISO 8601 formatted datetime
            limit=200,
            next_cursor=None
            ):
        '''
        Retrieves only created orders.  NOT acknowledged orders.
        '''
        base_url = '{}v3/orders/released?'.format(self.base_url)
        params = []
        if limit: params.append('limit={}'.format(limit))
        if next_cursor:
            next_cursor = next_cursor[1:]
            params.append('nextCursor={}'.format(next_cursor))
        if created_start_date: params.append('createdStartDate={}'.format(created_start_date))
        full_url = base_url + '&'.join(params)
        signature, timestamp = self.sign(full_url, 'GET')
        headers = self.get_headers(timestamp, signature)
        r = requests.get(full_url, headers=headers)
        return r

    def get_all_orders(
            self,
            sku=None,
            customer_order_id=None,
            purchase_order_id=None,
            status=None,                    # Created, Acknowledged, Shipped, Cancelled
            created_start_date=None,        # ISO 8601 formatted datetime
            created_end_date=None,
            from_expected_ship_date=None,
            to_expected_ship_date=None,
            limit=200,
            next_cursor=None
            ):
        '''
        '''
        base_url = '{}v3/orders?'.format(self.base_url)
        params = []
        if sku: params.append('sku={}'.format(sku))
        if customer_order_id: params.append('customerOrderId={}'.format(customer_order_id))
        if purchase_order_id: params.append('purchaseOrderId={}'.format(purchase_order_id))
        if status: params.append('status={}'.format(status))
        if created_start_date: params.append('createdStartDate={}'.format(created_start_date))
        if created_end_date: params.append('createdEndDate={}'.format(created_end_date))
        if from_expected_ship_date: params.append('fromExpectedShipDate={}'.format(from_expected_ship_date))
        if to_expected_ship_date: params.append('toExpectedShipDate={}'.format(to_expected_ship_date))
        if limit: params.append('limit={}'.format(limit))
        if next_cursor:
            next_cursor = next_cursor[1:]
            params.append('nextCursor={}'.format(next_cursor))
        full_url = base_url + '&'.join(params)
        signature, timestamp = self.sign(full_url, 'GET')
        headers = self.get_headers(timestamp, signature)
        r = requests.get(full_url, headers=headers)
        return r

    def ack_order(self, purchase_order_id):
        '''
        https://developer.walmartapis.com/#acknowledging-orders55
        "Acknowledge" order.  Whatever that means.
        '''
        full_url = '{}v3/orders/{}/acknowledge'.format(self.base_url, purchase_order_id)
        signature, timestamp = self.sign(full_url, 'POST')
        headers = self.get_headers(timestamp, signature)
        headers['content-type'] = 'application/xml'
        r = requests.post(full_url, headers=headers)
        return r

    def cancel_order_lines(self, purchase_order_id, data=[]):
        '''
        https://developer.walmartapis.com/#cancelling-order-lines56
        '''
        full_url = '{}v2/orders/{}/cancel'.format(self.base_url, purchase_order_id)
        # TODO: write it

    def refund_order_lines(self, purchase_order_id):
        '''
        '''
        full_url = '{}v3/orders/{}/refund'.format(self.base_url, purchase_order_id)
        # TODO: write it

    def update_shipping(self, purchase_order_id, data=[], status_default='Shipped', unit_of_measurement_default='EACH'):
        '''
        https://developer.walmartapis.com/#shipping-notificationsupdates58
        data is a list of dictionary objects with the line items...
            [{
                'line_number':          <lineNumber>,
                'status':               <status>,
                'quantity':             <amount>,
                'unit_of_measurement':  <unitOfMeasurement>,
                'ship_date_time':       <shipDateTime>,
                'carrier_name':         <carrierName>,
                'method_code':          <methodCode>,
                'tracking_number',      <trackingNumber>,
                'tracking_url',         <trackingURL>
            }, ...]
        '''
        full_url = '{}v3/orders/{}/shipping'.format(self.base_url, purchase_order_id)
        ns2 = 'http://walmart.com/mp/v3/orders'
        ns3 = 'http://walmart.com/'
        ns = 'ns2'
        order_shipment_elt = ET.Element('{}:orderShipment'.format(ns))
        order_shipment_elt.set('xmlns:ns2', ns2)
        order_shipment_elt.set('xmlns:ns3', ns3)
        order_lines_elt = ET.SubElement(order_shipment_elt, '{}:orderLines'.format(ns))
        for item in data:
            order_line_elt = ET.SubElement(order_lines_elt, '{}:orderLine'.format(ns))
            line_number_elt = ET.SubElement(order_line_elt, '{}:lineNumber'.format(ns))
            line_number_elt.text = item['line_number']
            order_line_statuses_elt = ET.SubElement(order_line_elt, '{}:orderLineStatuses'.format(ns))
            order_line_status_elt = ET.SubElement(order_line_statuses_elt, '{}:orderLineStatus'.format(ns))
            status_elt = ET.SubElement(order_line_status_elt, '{}:status'.format(ns))
            status_elt.text = item.get('status', status_default)
            status_quantity_elt = ET.SubElement(order_line_status_elt, '{}:statusQuantity'.format(ns))
            unit_of_measurement_elt = ET.SubElement(status_quantity_elt, '{}:unitOfMeasurement'.format(ns))
            unit_of_measurement_elt.text = item.get('unit_of_measurement', unit_of_measurement_default)
            amount_elt = ET.SubElement(status_quantity_elt, '{}:amount'.format(ns))
            amount_elt.text = item['quantity']
            tracking_info_elt = ET.SubElement(order_line_status_elt, '{}:trackingInfo'.format(ns))
            ship_date_time_elt = ET.SubElement(tracking_info_elt, '{}:shipDateTime'.format(ns))
            ship_date_time_elt.text = item['ship_date_time']
            carrier_name_elt = ET.SubElement(tracking_info_elt, '{}:carrierName'.format(ns))
            carrier_elt = ET.SubElement(carrier_name_elt, '{}:carrier'.format(ns))
            carrier_elt.text = item['carrier_name']
            method_code_elt = ET.SubElement(tracking_info_elt, '{}:methodCode'.format(ns))
            method_code_elt.text = item['method_code']
            tracking_number_elt = ET.SubElement(tracking_info_elt, '{}:trackingNumber'.format(ns))
            tracking_number_elt.text = item['tracking_number']
            if item.get('tracking_url', None):
                tracking_url_elt = ET.SubElement(tracking_info_elt, '{}:trackingURL'.format(ns))
                tracking_url_elt.text = item['tracking_url']
        xml_string = self.xml_head + ET.tostring(order_shipment_elt)
        sig, ts = self.sign(full_url, 'POST')
        headers = self.get_headers(ts, sig)
        headers['content-type'] = 'application/xml'
        r = requests.post(full_url, headers=headers, data=xml_string)
        return r        

    ###############################################################
    ###################### INVENTORY METHODS ######################
    ###############################################################

    def get_inventory(self, sku):
        '''
        https://developer.walmartapis.com/#get-inventory-for-an-item
        '''
        full_url = '{}v3/inventory?sku={}'.format(self.base_url, sku)
        signature, timestamp = self.sign(full_url, 'GET')
        headers = self.get_headers(timestamp, signature)
        r = requests.get(full_url, headers=headers)
        return r

    def update_inventory(self, sku, amount, unit='EACH', lag_time='2'):
        '''
        https://developer.walmartapis.com/#update-inventory-for-an-item
        updating inventory for single item
        '''
        full_url = '{}v3/inventory?sku={}'.format(self.base_url, sku)
        ns = 'wm'
        inventory_elt = ET.Element('{}:inventory'.format(ns))
        inventory_elt.set('xmlns:wm', 'http://walmart.com/')
        sku_elt = ET.SubElement(inventory_elt, '{}:sku'.format(ns))
        sku_elt.text = str(sku)
        quantity_elt = ET.SubElement(inventory_elt, '{}:quantity'.format(ns))
        unit_elt = ET.SubElement(quantity_elt, '{}:unit'.format(ns))
        unit_elt.text = unit
        amount_elt = ET.SubElement(quantity_elt, '{}:amount'.format(ns))
        amount_elt.text = str(amount)
        lag_elt = ET.SubElement(inventory_elt, '{}:fulfillmentLagTime'.format(ns))
        lag_elt.text = lag_time
        xml_string = '{}{}'.format(self.xml_head, ET.tostring(inventory_elt))
        signature, timestamp = self.sign(full_url, 'PUT')
        headers = self.get_headers(timestamp, signature)
        headers['content-type'] = 'application/xml'
        r = requests.put(full_url, headers=headers, data=xml_string)
        return r

    def bulk_update_inventory(self, version='1.4', data=[]):
        '''
        https://developer.walmartapis.com/#bulk-update-inventory
        data is a list of dictionaries -> 
            [{'sku': <sku>, 'unit': <unit>, 'amount': <amount>, 'lag_time': <lag_time>}, ...]
        uses memory file (StringIO) to send xml file
        '''
        full_url = '{}v3/feeds?feedType=inventory'.format(self.base_url)
        ns = 'http://walmart.com/'
        inventory_feed_elt = ET.Element('InventoryFeed')
        inventory_feed_elt.set('xmlns', ns)
        inventory_header_elt = ET.SubElement(inventory_feed_elt, 'InventoryHeader')
        version_elt = ET.SubElement(inventory_header_elt, 'version')
        version_elt.text = version
        for item in data:
            inventory_elt = ET.SubElement(inventory_feed_elt, 'inventory')
            sku_elt = ET.SubElement(inventory_elt, 'sku')
            sku_elt.text = str(item['sku'])
            quantity_elt = ET.SubElement(inventory_elt, 'quantity')
            unit_elt = ET.SubElement(quantity_elt, 'unit')
            unit_elt.text = item['unit']
            amount_elt = ET.SubElement(quantity_elt, 'amount')
            amount_elt.text = str(item['amount'])
            lag_elt = ET.SubElement(inventory_elt, 'fulfillmentLagTime')
            lag_elt.text = str(item['lag_time'])
        xml_string = ET.tostring(inventory_feed_elt)
        files = {'file': ('bulk.xml', xml_string)}
        signature, timestamp = self.sign(full_url, 'POST')
        headers = self.get_headers(timestamp, signature)
        headers['Content-Type'] = 'multipart/form-data;'
        r = requests.post(full_url, headers=headers, files=files)
        return r

    ###############################################################
    ####################### REPORT METHODS ########################
    ###############################################################

    def get_item_report(self, cleaned=True):
        '''
        returns response object -> zipped csv file
        if cleaned is set to True, then a tuple (response, data) is returned
        '''
        full_url = '{}v2/getReport?type=item'.format(self.base_url)
        sig, ts = self.sign(full_url, 'GET')
        headers = self.get_headers(ts, sig)
        headers['Content-Type'] = 'application/xml'
        r = requests.get(full_url, headers=headers)
        if cleaned:
            data = clean_report(r.content)
            return r, data
        return r

    def get_buy_box_report(self, cleaned=True):
        full_url = '{}v2/getReport?type=buybox'.format(self.base_url)
        sig, ts = self.sign(full_url, 'GET')
        headers = self.get_headers(ts, sig)
        headers['Content-Type'] = 'application/xml'
        r = requests.get(full_url, headers=headers)
        if cleaned:
            data = clean_report(r.content)
            return r, data
        return r