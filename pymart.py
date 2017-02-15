'''
wrapper around the walmart api
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
try:
    # python 2
    from StringIO import StringIO
except:
    # python 3
    from IO import StringIO


__author__ = 'Brian Perrett'
__date__   = 'Feb 10, 2017'


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
            # 'Host': 'https://marketplace.walmartapis.com'
            }
        return headers

    def sign(self, full_url, request_method):
        '''
        use the cryptography library to sign a specific string
        returns a tuple as (signature[string], timestamp[milliseconds])
        '''
        timestamp = str(int(time.time() * 1000))
        string_to_sign = '{consumer_id}\n{full_url}\n{http_method}\n{timestamp}\n'.format(**{
                'consumer_id': self.consumer_id,
                'full_url': full_url,
                'http_method': request_method.upper(),
                'timestamp': timestamp
                })
        # string_to_sign.encode('utf-8')
        # print(string_to_sign)
        pem_format = '-----BEGIN PRIVATE KEY-----\n{}\n-----END PRIVATE KEY-----'.format(self.private_key)
        # print(pem_format)
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

    ###########################################################
    ###################### ORDER METHODS ######################
    ###########################################################

    def get_order(self, order_id):
        '''
        '''
        full_url = '{}v2/orders/{}'.format(self.base_url, order_id)
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
        base_url = '{}v2/orders?'.format(self.base_url)
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
        if next_cursor: params.append('nextCursor={}'.format(next_cursor))
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
        full_url = '{}v2/orders/{}/acknowledge'.format(self.base_url, purchase_order_id)
        signature, timestamp = self.sign(full_url, 'POST')
        headers = self.get_headers(timestamp, signature)
        headers['content-type'] = 'application/xml'
        r = requests.post(full_url, headers=headers)
        return r

    def cancel_order_lines(self, purchase_order_id, line_number, status):
        '''
        https://developer.walmartapis.com/#cancelling-order-lines56
        '''
        full_url = '{}v2/orders/{}/cancel'.format(self.base_url, purchase_order_id)

    def update_shipping(
            self,
            purchase_order_id,
            line_number,
            status,
            ship_date_time,
            carrier_name,
            method_code,
            tracking_number,
            tracking_url=None
            ):
        '''
        https://developer.walmartapis.com/#shipping-notificationsupdates58
        '''
        full_url = '{}/v2/orders/{}/shipping'.format(self.base_url, purchase_order_id)
        ns2 = 'http://walmart.com/mp/orders'
        ns3 = 'http://walmart.com/'
        order_shipment_elt = ET.Element('{}:orderShipment')
        order_shipment_elt.set('xmlns:ns2', ns2)
        order_shipment_elt.set('xmlns:ns3', ns3)
        # TODO: finish method.

    ###############################################################
    ###################### INVENTORY METHODS ######################
    ###############################################################

    def get_inventory(self, sku):
        '''
        https://developer.walmartapis.com/#get-inventory-for-an-item
        '''
        full_url = '{}v2/inventory?sku={}'.format(self.base_url, sku)
        signature, timestamp = self.sign(full_url, 'GET')
        headers = self.get_headers(timestamp, signature)
        r = requests.get(full_url, headers=headers)
        return r

    def update_inventory(self, sku, amount, unit='EACH', lag_time='2'):
        '''
        https://developer.walmartapis.com/#update-inventory-for-an-item
        updating inventory for single item
        '''
        full_url = '{}v2/inventory?sku={}'.format(self.base_url, sku)
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
        full_url = '{}v2/feeds?feedType=inventory'.format(self.base_url)
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
