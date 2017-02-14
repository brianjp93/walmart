'''
wrapper around the walmart api
'''
import requests
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


__author__ = 'Brian Perrett'
__date__   = 'Feb 10, 2017'


class Walmart():
    base_url = 'https://marketplace.walmartapis.com/'
    def __init__(self, private_key, consumer_id):
        self.private_key = private_key
        self.consumer_id = consumer_id

    def get_headers(self, timestamp, signature):
        random_id = str(uuid4())
        headers = {
            'Accept': 'application/xml',
            'WM_SVC.NAME': 'Walmart Marketplace',
            'WM_CONSUMER.ID': '{}'.format(self.consumer_id),
            'WM_SEC.TIMESTAMP': str(timestamp),
            'WM_SEC.AUTH_SIGNATURE': signature,
            'WM_QOS.CORRELATION_ID': random_id
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
        signature, timestamp = self.sign(full_url, 'POST')
        headers = self.get_headers(timestamp, signature)
        r = requests.get(full_url, headers=headers)
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