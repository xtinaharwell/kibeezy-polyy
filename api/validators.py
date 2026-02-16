"""
Validation utilities for API inputs
"""
import re
from decimal import Decimal
from django.core.exceptions import ValidationError


class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, message, code=None):
        self.message = message
        self.code = code or 'invalid'
        super().__init__(self.message)


def validate_phone_number(phone_number):
    """
    Validate Kenyan phone number format
    Accepts: 254xxxxxxxxx or 0xxxxxxxxx
    """
    phone = str(phone_number).replace('+', '').replace(' ', '').replace('-', '')
    
    # Format: 254 followed by 9 digits (Kenyan number starting with country code)
    # Or: 0 followed by 9 digits (local format)
    patterns = [
        r'^254\d{9}$',      # International format
        r'^0\d{9}$',        # Local format
        r'^\+254\d{9}$'     # Alternative international format
    ]
    
    for pattern in patterns:
        if re.match(pattern, phone):
            return phone
    
    raise ValidationError('Phone number must be in format 254xxxxxxxxx or 0xxxxxxxxx')


def validate_amount(amount, min_amount=Decimal('1'), max_amount=Decimal('150000')):
    """
    Validate transaction amount
    Default range: 1 KES to 150,000 KES
    """
    try:
        amount_decimal = Decimal(str(amount))
    except:
        raise ValidationError('Amount must be a valid number')
    
    if amount_decimal < min_amount:
        raise ValidationError(f'Amount must be at least {min_amount} KES')
    
    if amount_decimal > max_amount:
        raise ValidationError(f'Amount cannot exceed {max_amount} KES')
    
    return amount_decimal


def validate_market_question(question):
    """Validate market question"""
    if not question or len(question) < 10:
        raise ValidationError('Question must be at least 10 characters')
    
    if len(question) > 255:
        raise ValidationError('Question cannot exceed 255 characters')
    
    # Basic profanity check (simple version)
    profanities = ['offensive', 'hate', 'illegal']  # Add more as needed
    question_lower = question.lower()
    
    for word in profanities:
        if word in question_lower:
            raise ValidationError(f'Question contains inappropriate content')
    
    return question


def validate_bet_outcome(outcome):
    """Validate bet outcome"""
    if outcome not in ['Yes', 'No']:
        raise ValidationError('Outcome must be "Yes" or "No"')
    
    return outcome


def validate_market_category(category):
    """Validate market category"""
    valid_categories = [
        'Politics',
        'Sports',
        'Technology',
        'Entertainment',
        'Business',
        'Science',
        'Health',
        'Other'
    ]
    
    if category not in valid_categories:
        raise ValidationError(f'Category must be one of: {", ".join(valid_categories)}')
    
    return category


def validate_otp(otp):
    """Validate OTP format"""
    otp = str(otp).strip()
    
    if not otp or len(otp) != 6:
        raise ValidationError('OTP must be 6 digits')
    
    if not otp.isdigit():
        raise ValidationError('OTP must contain only digits')
    
    return otp


def validate_full_name(full_name):
    """Validate user full name"""
    if not full_name or len(full_name) < 2:
        raise ValidationError('Full name must be at least 2 characters')
    
    if len(full_name) > 255:
        raise ValidationError('Full name cannot exceed 255 characters')
    
    return full_name


def validate_pin(pin):
    """Validate user PIN"""
    pin = str(pin)
    
    if len(pin) != 4:
        raise ValidationError('PIN must be exactly 4 digits')
    
    if not pin.isdigit():
        raise ValidationError('PIN must contain only digits')
    
    return pin


def validate_string(value, min_length=1, max_length=255, field_name='Value'):
    """Generic string validation"""
    if not value or len(str(value)) < min_length:
        raise ValidationError(f'{field_name} must be at least {min_length} characters')
    
    if len(str(value)) > max_length:
        raise ValidationError(f'{field_name} cannot exceed {max_length} characters')
    
    return value


def validate_date_string(date_string):
    """Validate ISO format date string"""
    from datetime import datetime
    
    try:
        return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    except:
        raise ValidationError('Date must be in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)')
