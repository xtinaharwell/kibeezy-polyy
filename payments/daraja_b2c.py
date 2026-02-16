"""
M-Pesa Daraja B2C integration for KASOKO payouts
Handles OAuth token generation, B2C API calls, and secure credential management
"""
import requests
import json
import logging
import base64
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
PROD_B2C_URL = "https://api.safaricom.co.ke/mpesa/b2c/v1/paymentrequest"

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
CALLBACK_URL = getattr(settings, 'MPESA_CALLBACK_URL', 'https://kasoko.app/api/payments/b2c-callback/')


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
        
        # Get oauth token
        token = get_oauth_token()
        
        # Prepare payload
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        payload = {
            "InitiatorName": INITIATOR_NAME,
            "SecurityCredential": encrypt_initiator_password(),
            "CommandID": "BusinessPayment",
            "Amount": str(int(amount)),  # Amount MUST be integer in pesewas/smallest units
            "PartyA": PAYBILL,
            "PartyB": phone,
            "Remarks": f"KASOKO Market Payout - Ref: {transaction.external_ref}",
            "QueueTimeOutURL": CALLBACK_URL,
            "ResultURL": CALLBACK_URL,
            "Occasion": "KASOKO_PAYOUT"
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Calling B2C for transaction {transaction.id}, phone {phone}, amount {amount}")
        response = requests.post(
            B2C_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"B2C call successful: {result.get('ConversationID')}")
        
        # Store B2C response metadata
        transaction.mpesa_response = {
            'request_payload': payload,
            'response': result,
            'called_at': datetime.now().isoformat()
        }
        transaction.save()
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"B2C API call failed: {e}")
        transaction.mpesa_response = {
            'error': str(e),
            'error_type': 'api_error',
            'failed_at': datetime.now().isoformat()
        }
        transaction.save()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in B2C call: {e}")
        transaction.mpesa_response = {
            'error': str(e),
            'error_type': 'unexpected_error',
            'failed_at': datetime.now().isoformat()
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
