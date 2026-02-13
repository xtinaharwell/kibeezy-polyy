import requests
import base64
from datetime import datetime
from django.conf import settings

class MpesaClient:
    def __init__(self):
        self.consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', 'placeholder')
        self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', 'placeholder')
        self.shortcode = getattr(settings, 'MPESA_SHORTCODE', '174379')
        self.passkey = getattr(settings, 'MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')
        self.base_url = "https://sandbox.safaricom.co.ke"

    def get_token(self):
        auth_url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        response = requests.get(auth_url, auth=(self.consumer_key, self.consumer_secret))
        if response.status_code == 200:
            return response.json().get('access_token')
        return None

    def stk_push(self, phone_number, amount, callback_url, reference="PolyDeposit", description="Deposit to Poly"):
        token = self.get_token()
        if not token:
            return {"error": "Failed to get access token"}

        # Format phone number to 254...
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('+'):
            phone_number = phone_number[1:]
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(f"{self.shortcode}{self.passkey}{timestamp}".encode()).decode()

        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": reference,
            "TransactionDesc": description
        }

        stk_url = f"{self.base_url}/mpesa/stkpush/v1/query" if False else f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        response = requests.post(stk_url, json=payload, headers=headers)
        return response.json()
