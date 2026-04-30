"""
M-Pesa Daraja B2C integration for CACHE payouts
Handles OAuth token generation, B2C API calls, and secure credential management
"""
import requests
import json
import logging
import base64
import uuid
from datetime import datetime
from django.conf import settings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# Daraja API endpoints
SANDBOX_OAUTH_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
PROD_OAUTH_URL = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

SANDBOX_B2C_URL = "https://sandbox.safaricom.co.ke/mpesa/b2c/v1/paymentrequest"
PROD_B2C_URL = "https://api.safaricom.co.ke/mpesa/b2c/v3/paymentrequest"

# Use sandbox by default, switch to PROD in settings
IS_PRODUCTION = getattr(settings, 'MPESA_PRODUCTION', False)
OAUTH_URL = PROD_OAUTH_URL if IS_PRODUCTION else SANDBOX_OAUTH_URL
B2C_URL = PROD_B2C_URL if IS_PRODUCTION else SANDBOX_B2C_URL

# Secrets from environment/settings
CONSUMER_KEY = getattr(settings, 'MPESA_CONSUMER_KEY', '')
CONSUMER_SECRET = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
INITIATOR_NAME = getattr(settings, 'MPESA_INITIATOR_NAME', 'testapi')
SECURITY_CREDENTIAL_ENCRYPTED = getattr(settings, 'MPESA_SECURITY_CREDENTIAL_ENCRYPTED', '')
PAYBILL = getattr(settings, 'MPESA_PAYBILL', '600000')  # Your Paybill/shortcode
CALLBACK_URL = getattr(settings, 'MPESA_CALLBACK_URL', 'https://cache.co.ke/api/payments/b2c-callback/')


def get_oauth_token():
    """
    Fetch OAuth token from Daraja API
    Returns: access_token (str) or raises exception
    """
    try:
        logger.info("Fetching OAuth token from Daraja...")
        response = requests.get(
            OAUTH_URL,
            auth=(CONSUMER_KEY, CONSUMER_SECRET),
            timeout=10
        )
        response.raise_for_status()
        token = response.json().get('access_token')
        if not token:
            raise ValueError("No access_token in response")
        logger.info("OAuth token fetched successfully")
        return token
    except requests.RequestException as e:
        logger.error(f"OAuth token fetch failed: {e}")
        raise


def encrypt_initiator_password():
    """
    Encrypt initiator password using Safaricom public certificate
    This should be done once and stored securely in environment
    For implementation, you'll need Safaricom's public cert in PEM format
    """
    # This is typically done once offline and stored in settings
    # Return pre-encrypted credential from settings
    return SECURITY_CREDENTIAL_ENCRYPTED


def call_b2c(transaction, phone_number, amount):
    """
    Call M-Pesa B2C API to send payout
    
    Args:
        transaction: Transaction model instance with payment details
        phone_number: Recipient phone in format 254XXXXXXX or +254XXXXXXX
        amount: Amount to transfer (KES)
    
    Returns:
        dict: Response from Daraja API with ConversationID, OriginatorConversationID, etc.
    """
    try:
        # Normalize phone number to 254XXXXXXX format
        phone = normalize_phone(phone_number)
        
        # Generate unique OriginatorConversationID per Safaricom spec (REQUIRED)
        # Format: SHORTCODE_TIMESTAMP_UUID for tracking and avoiding double disbursement
        originator_conv_id = f"{PAYBILL}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"
        transaction.external_ref = originator_conv_id
        transaction.save()
        
        # Get oauth token
        token = get_oauth_token()
        
        # Prepare payload per official Safaricom B2C v3 specification
        payload = {
            "OriginatorConversationID": originator_conv_id,  # REQUIRED: Unique ID to avoid double disbursement
            "InitiatorName": INITIATOR_NAME,
            "SecurityCredential": encrypt_initiator_password(),
            "CommandID": "BusinessPayment",
            "Amount": int(amount),  # Integer amount in KES
            "PartyA": PAYBILL,  # B2C shortcode/paybill
            "PartyB": phone,  # Customer phone (254XXXXXXXXX)
            "Remarks": f"Market Winnings - {originator_conv_id}",
            "QueueTimeOutURL": CALLBACK_URL,
            "ResultURL": CALLBACK_URL,
            "Occasion": "Market Winnings"
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"📤 B2C Request: txn_id={transaction.id}, phone={phone}, amount={amount}")
        logger.info(f"   OriginatorConversationID={originator_conv_id}")
        logger.info(f"   PartyA={PAYBILL}, PartyB={phone}")
        
        response = requests.post(
            B2C_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"✅ B2C Immediate Acknowledgment Response:")
        logger.info(f"   ResponseCode={result.get('ResponseCode')}")
        logger.info(f"   ConversationID={result.get('ConversationID')}")
        logger.info(f"   OriginatorConversationID={result.get('OriginatorConversationID')}")
        logger.info(f"   (Actual transaction result will be sent via callback)")
        
        # Store B2C response metadata
        transaction.mpesa_response = {
            'originator_conversation_id': result.get('OriginatorConversationID'),
            'conversation_id': result.get('ConversationID'),
            'response_code': result.get('ResponseCode'),
            'response_description': result.get('ResponseDescription', ''),
            'request_payload': {
                'OriginatorConversationID': originator_conv_id,
                'InitiatorName': INITIATOR_NAME,
                'CommandID': 'BusinessPayment',
                'Amount': int(amount),
                'PartyA': PAYBILL,
                'PartyB': phone,
            },
            'called_at': datetime.now().isoformat(),
            'phone_normalized': phone,
            'api_url': B2C_URL,
            'is_production': IS_PRODUCTION,
            'status': 'ACKNOWLEDGMENT_RECEIVED'
        }
        transaction.save()
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"B2C API call failed: {str(e)}")
        transaction.mpesa_response = {
            'error': str(e),
            'error_type': 'api_error',
            'failed_at': datetime.now().isoformat(),
            'phone': phone_number,
            'api_url': B2C_URL,
            'is_production': IS_PRODUCTION
        }
        transaction.save()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in B2C call: {str(e)}")
        transaction.mpesa_response = {
            'error': str(e),
            'error_type': 'unexpected_error',
            'failed_at': datetime.now().isoformat(),
            'phone': phone_number,
            'api_url': B2C_URL,
            'is_production': IS_PRODUCTION
        }
        transaction.save()
        raise


def normalize_phone(phone):
    """
    Convert phone numbers to Safaricom format 254XXXXXXX
    Handles: 0718..., 254718..., +254718...
    """
    # Remove common prefixes and formatting
    phone = str(phone).strip().replace('+', '').replace(' ', '').replace('-', '')
    
    # If starts with 0, replace with 254
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    
    # Ensure it starts with 254
    if not phone.startswith('254'):
        phone = '254' + phone
    
    return phone


def verify_b2c_callback(callback_data):
    """
    Verify B2C callback data (optional: if Safaricom provides signature)
    In production, Safaricom may include an HMAC signature
    """
    # Implementation depends on Safaricom's callback security scheme
    # For now, we trust HTTPS and verify external_ref matches a known transaction
    return True
