import os
import json
import requests
from decimal import Decimal
from datetime import datetime
import logging
from decouple import config

logger = logging.getLogger(__name__)

class MpesaIntegration:
    """
    Real M-Pesa integration for STK Push payments
    """
    
    def __init__(self):
        self.consumer_key = config('MPESA_CONSUMER_KEY', default='test_key')
        self.consumer_secret = config('MPESA_CONSUMER_SECRET', default='test_secret')
        self.shortcode = config('MPESA_SHORTCODE', default='174379')
        self.passkey = config('MPESA_PASSKEY', default='test_passkey')
        self.base_url = 'https://sandbox.safaricom.co.ke'  # Use sandbox for testing
        self.access_token = None
        self.token_expiry = None
    
    def get_access_token(self):
        """Get OAuth access token from M-Pesa"""
        try:
            auth = (self.consumer_key, self.consumer_secret)
            endpoint = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
            
            response = requests.get(endpoint, auth=auth, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data.get('access_token')
            self.token_expiry = datetime.now()
            
            logger.info("M-Pesa access token generated successfully")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to get M-Pesa access token: {str(e)}")
            raise
    
    def get_valid_token(self):
        """Get valid access token, refresh if needed"""
        if not self.access_token or not self.token_expiry:
            return self.get_access_token()
        
        # Token expires in 3600 seconds, refresh at 1 hour mark
        from datetime import timedelta
        if datetime.now() - self.token_expiry > timedelta(minutes=59):
            return self.get_access_token()
        
        return self.access_token
    
    def initiate_stk_push(self, phone_number, amount, account_reference='Kibeezy'):
        """
        Initiate STK push for payment collection
        
        Args:
            phone_number: Valid M-Pesa phone number (254xxxxxxxxx)
            amount: Amount in KES
            account_reference: Transaction reference
            
        Returns:
            {
                'CheckoutRequestID': '...',
                'ResponseCode': '0',
                'ResponseDescription': '...',
                'CustomerMessage': '...',
                'MerchantRequestID': '...'
            }
        """
        try:
            # Normalize phone number (remove +, add 254 if not present)
            phone_number = str(phone_number).replace('+', '').replace(' ', '')
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            elif not phone_number.startswith('254'):
                phone_number = '254' + phone_number
            
            # Validate phone number
            if not self._validate_phone_number(phone_number):
                return {
                    'ResponseCode': '1',
                    'ResponseDescription': 'Invalid phone number format',
                    'CustomerMessage': 'Please enter a valid M-Pesa phone number'
                }
            
            # Validate amount
            amount = Decimal(str(amount))
            if amount < 1 or amount > 150000:
                return {
                    'ResponseCode': '1',
                    'ResponseDescription': 'Invalid amount',
                    'CustomerMessage': 'Amount must be between 1 and 150,000 KES'
                }
            
            # Generate timestamp and password
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = self._generate_password(timestamp)
            
            token = self.get_valid_token()
            
            endpoint = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            payload = {
                'BusinessShortCode': self.shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': int(amount),
                'PartyA': phone_number,
                'PartyB': self.shortcode,
                'PhoneNumber': phone_number,
                'CallBackURL': self._get_callback_url(),
                'AccountReference': account_reference,
                'TransactionDesc': f'Kibeezy deposit: {account_reference}'
            }
            
            logger.info(f"Initiating STK push for {phone_number}, amount: {amount}")
            
            response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"STK Push initiated: {data}")
            
            return {
                'CheckoutRequestID': data.get('CheckoutRequestID'),
                'ResponseCode': data.get('ResponseCode'),
                'ResponseDescription': data.get('ResponseDescription'),
                'CustomerMessage': data.get('CustomerMessage'),
                'MerchantRequestID': data.get('MerchantRequestID')
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"M-Pesa API request failed: {str(e)}")
            return {
                'ResponseCode': '1',
                'ResponseDescription': 'Network error',
                'CustomerMessage': 'Payment service temporarily unavailable. Please try again.'
            }
        except Exception as e:
            logger.error(f"STK Push error: {str(e)}")
            return {
                'ResponseCode': '1',
                'ResponseDescription': str(e),
                'CustomerMessage': 'An error occurred. Please try again.'
            }
    
    def query_transaction_status(self, checkout_request_id):
        """Query the status of a transaction"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = self._generate_password(timestamp)
            
            token = self.get_valid_token()
            
            endpoint = f"{self.base_url}/mpesa/stkpushquery/v1/query"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            payload = {
                'BusinessShortCode': self.shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'CheckoutRequestID': checkout_request_id
            }
            
            response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Transaction status query failed: {str(e)}")
            return None
    
    def validate_callback(self, callback_data):
        """Validate and process M-Pesa callback"""
        try:
            body = callback_data.get('Body', {})
            stk_callback = body.get('stkCallback', {})
            
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc', '')
            
            if result_code == 0:
                # Payment successful
                callback_metadata = stk_callback.get('CallbackMetadata', {})
                items = callback_metadata.get('Item', [])
                
                transaction_data = {}
                for item in items:
                    name = item.get('Name')
                    value = item.get('Value')
                    
                    if name == 'Amount':
                        transaction_data['amount'] = Decimal(str(value))
                    elif name == 'MpesaReceiptNumber':
                        transaction_data['receipt_number'] = value
                    elif name == 'TransactionDate':
                        transaction_data['transaction_date'] = value
                    elif name == 'PhoneNumber':
                        transaction_data['phone_number'] = str(value)
                
                transaction_data['checkout_request_id'] = stk_callback.get('CheckoutRequestID')
                transaction_data['merchant_request_id'] = stk_callback.get('MerchantRequestID')
                transaction_data['status'] = 'COMPLETED'
                transaction_data['result_code'] = result_code
                
                logger.info(f"Payment successful: {transaction_data}")
                return transaction_data
            
            else:
                # Payment failed
                logger.warning(f"Payment failed: {result_desc}")
                return {
                    'status': 'FAILED',
                    'result_code': result_code,
                    'result_desc': result_desc,
                    'checkout_request_id': stk_callback.get('CheckoutRequestID')
                }
        
        except Exception as e:
            logger.error(f"Callback validation error: {str(e)}")
            return None
    
    def _generate_password(self, timestamp):
        """Generate M-Pesa password"""
        import base64
        password_string = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(password_string.encode()).decode()
    
    def _validate_phone_number(self, phone_number):
        """Validate M-Pesa phone number format"""
        # Must be 254 followed by 9 digits (254xxxxxxxxx)
        return bool(len(phone_number) == 12 and phone_number.startswith('254') and phone_number.isdigit())
    
    def _get_callback_url(self):
        """Get callback URL for M-Pesa"""
        return config(
            'MPESA_CALLBACK_URL',
            default='https://yourdomain.com/api/payments/callback/'
        )


# For development/testing without real M-Pesa
class MockMpesaIntegration:
    """Mock M-Pesa for development"""
    
    def initiate_stk_push(self, phone_number, amount, account_reference='Kibeezy'):
        """Mock STK push"""
        logger.info(f"[MOCK] STK Push for {phone_number}, amount: {amount}")
        return {
            'CheckoutRequestID': 'ws_CO_DMZ_123456789',
            'ResponseCode': '0',
            'ResponseDescription': 'Success. Request accepted for processing',
            'CustomerMessage': 'Please enter your M-Pesa PIN (MOCK)',
            'MerchantRequestID': 'test_merchant_123'
        }
    
    def query_transaction_status(self, checkout_request_id):
        """Mock status query"""
        return {
            'ResultCode': 0,
            'ResultDesc': 'Success'
        }
    
    def validate_callback(self, callback_data):
        """Mock callback validation"""
        return {
            'status': 'COMPLETED',
            'amount': Decimal('100'),
            'receipt_number': 'LHD7FHFF6EF',
            'transaction_date': '20260214120000',
            'phone_number': '254712345678',
            'checkout_request_id': callback_data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
        }


def get_mpesa_client():
    """Factory function to get M-Pesa client"""
    if config('MPESA_DEBUG', default=True, cast=bool):
        logger.info("Using Mock M-Pesa Client")
        return MockMpesaIntegration()
    
    logger.info("Using Real M-Pesa Client")
    return MpesaIntegration()
