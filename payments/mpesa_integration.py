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
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_retries}: Getting M-Pesa access token...")
                logger.info(f"Consumer Key: {self.consumer_key[:10]}...")
                logger.info(f"Endpoint: {self.base_url}/oauth/v1/generate")
                
                auth = (self.consumer_key, self.consumer_secret)
                endpoint = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
                
                response = requests.get(endpoint, auth=auth, timeout=30)  # Increased timeout
                
                logger.info(f"Token response status: {response.status_code}")
                logger.info(f"Token response text: {response.text}")
                
                response.raise_for_status()
                
                data = response.json()
                self.access_token = data.get('access_token')
                self.token_expiry = datetime.now()
                
                if not self.access_token:
                    logger.error(f"No access_token in response: {data}")
                    raise Exception(f"M-Pesa response missing access_token: {data}")
                
                logger.info(f"✅ M-Pesa access token generated successfully")
                logger.info(f"Token (first 20 chars): {self.access_token[:20]}...")
                return self.access_token
                
            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ Attempt {attempt + 1}: Timeout (30s). Retrying...")
                if attempt == max_retries - 1:
                    error_msg = "M-Pesa API timeout after 3 attempts (Safaricom API is slow or unreachable)"
                    logger.error(f"❌ {error_msg}")
                    raise Exception(error_msg)
                continue
                
            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP Error {e.response.status_code}: {e.response.text}"
                logger.error(f"❌ Attempt {attempt + 1}: {error_msg}")
                if attempt == max_retries - 1:
                    raise Exception(error_msg)
                continue
                
            except Exception as e:
                logger.error(f"❌ Attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                continue
        
        raise Exception("Failed to get M-Pesa token after all retries")
    
    def get_valid_token(self):
        """Get valid access token, refresh if needed"""
        if not self.access_token or not self.token_expiry:
            logger.info("No cached token, fetching new one...")
            return self.get_access_token()
        
        # Token expires in 3600 seconds, refresh at 59 minute mark
        from datetime import timedelta
        time_diff = datetime.now() - self.token_expiry
        if time_diff > timedelta(minutes=59):
            logger.info(f"Token expired ({time_diff.total_seconds()}s ago), fetching new one...")
            return self.get_access_token()
        
        logger.info(f"Using cached token (generated {time_diff.total_seconds():.0f}s ago)")
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
            
            logger.info(f"Getting valid token for STK push...")
            token = self.get_valid_token()
            logger.info(f"Using token (first 20 chars): {token[:20]}...")
            
            endpoint = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            logger.info(f"Authorization header: Bearer {token[:20]}...")
            
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
            
            logger.info(f"📤 Sending STK Push request to: {endpoint}")
            logger.info(f"   Phone: {phone_number}, Amount: {amount}")
            logger.info(f"   Token: {token[:30]}...")
            logger.info(f"   Callback: {payload.get('CallBackURL')}")
            
            response = requests.post(endpoint, json=payload, headers=headers, timeout=30)  # Increased timeout
            
            logger.info(f"📥 STK Push response status: {response.status_code}")
            logger.info(f"   Response: {response.text}")
            
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ STK Push initiated successfully: {data}")
            
            return {
                'CheckoutRequestID': data.get('CheckoutRequestID'),
                'ResponseCode': data.get('ResponseCode'),
                'ResponseDescription': data.get('ResponseDescription'),
                'CustomerMessage': data.get('CustomerMessage'),
                'MerchantRequestID': data.get('MerchantRequestID')
            }
            
        except requests.exceptions.HTTPError as e:
            # Log the response body for debugging
            error_response = ""
            try:
                error_response = e.response.json()
            except:
                error_response = e.response.text
            
            logger.error(f"M-Pesa API HTTP Error {e.response.status_code}: {error_response}")
            logger.error(f"Request payload was: {payload}")
            
            return {
                'ResponseCode': '1',
                'ResponseDescription': f'M-Pesa API Error: {error_response}',
                'CustomerMessage': 'Payment service error. Please contact support.'
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
    
    def b2c_payment(self, phone_number, amount, description='Kibeezy Withdrawal'):
        """
        B2C payment for withdrawals/payouts
        
        Args:
            phone_number: Receiving phone number (0xxxxxxxxx or 254xxxxxxxxx)
            amount: Amount in KES
            description: Transaction description
            
        Returns:
            {
                'ConversationID': '...',
                'OriginatorConversationID': '...',
                'ResponseCode': '0',
                'ResponseDescription': '...'
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
            if amount < 10 or amount > 150000:
                return {
                    'ResponseCode': '1',
                    'ResponseDescription': 'Invalid amount',
                    'CustomerMessage': 'Amount must be between 10 and 150,000 KES'
                }
            
            token = self.get_valid_token()
            
            # B2C requires initiating user credentials (Business to Customer)
            # Using shortcode as initiating user for now
            initiating_identifier = self.shortcode  # Paybill number
            identifier_type = '4'  # 4 = Paybill; 2 = Till number
            
            endpoint = f"{self.base_url}/mpesa/b2c/v1/paymentrequest"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            payload = {
                'InitiatorName': 'Kibeezy',
                'SecurityCredential': self._get_security_credential(),
                'CommandID': 'BusinessPayment',  # For regular payouts
                'Amount': int(amount),
                'PartyA': initiating_identifier,
                'PartyB': phone_number,
                'Remarks': description,
                'QueueTimeOutURL': self._get_b2c_callback_url(),
                'ResultURL': self._get_b2c_callback_url(),
                'Occasion': 'KIBEEZY_WITHDRAWAL'
            }
            
            logger.info(f"📤 Sending B2C Payment request to: {endpoint}")
            logger.info(f"   Recipient: {phone_number}, Amount: {amount}")
            logger.info(f"   Initiator: {initiating_identifier}")
            
            response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
            
            logger.info(f"📥 B2C Payment response status: {response.status_code}")
            logger.info(f"   Response: {response.text}")
            
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ B2C Payment initiated successfully: {data}")
            
            return {
                'ConversationID': data.get('ConversationID'),
                'OriginatorConversationID': data.get('OriginatorConversationID'),
                'ResponseCode': data.get('ResponseCode'),
                'ResponseDescription': data.get('ResponseDescription'),
                'RequestId': data.get('RequestId')
            }
            
        except requests.exceptions.HTTPError as e:
            error_response = ""
            try:
                error_response = e.response.json()
            except:
                error_response = e.response.text
            
            logger.error(f"M-Pesa B2C API HTTP Error {e.response.status_code}: {error_response}")
            
            return {
                'ResponseCode': '1',
                'ResponseDescription': f'M-Pesa API Error: {error_response}',
                'CustomerMessage': 'Withdrawal service error. Please contact support.'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"M-Pesa B2C API request failed: {str(e)}")
            return {
                'ResponseCode': '1',
                'ResponseDescription': 'Network error',
                'CustomerMessage': 'Withdrawal service temporarily unavailable. Please try again.'
            }
        except Exception as e:
            logger.error(f"B2C Payment error: {str(e)}")
            return {
                'ResponseCode': '1',
                'ResponseDescription': str(e),
                'CustomerMessage': 'An error occurred. Please try again.'
            }
    
    def _get_security_credential(self):
        """Get security credential for B2C - in real scenario this would be encrypted"""
        # For sandbox/testing, return a placeholder
        # In production, this would be an encrypted password
        return config('MPESA_B2C_SECURITY_CREDENTIAL', default='test_credential')
    
    def _get_b2c_callback_url(self):
        """Get B2C callback URL"""
        return config(
            'MPESA_B2C_CALLBACK_URL',
            default=config('MPESA_CALLBACK_URL', default='https://yourdomain.com/api/payments/b2c-callback/')
        )
    
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
            
            response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
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


def get_mpesa_client():
    """Factory function to get M-Pesa client - Always uses real M-Pesa Daraja API"""
    logger.info("Using Real M-Pesa Daraja API")
    return MpesaIntegration()
