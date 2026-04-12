"""
Enhanced validation utilities for API inputs
Includes SQL injection prevention, XSS protection, and comprehensive input validation
"""
import re
import html
from decimal import Decimal
from django.core.exceptions import ValidationError as DjangoValidationError
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, message, code=None):
        self.message = message
        self.code = code or 'invalid'
        super().__init__(self.message)


# ============================================================================
# SQL INJECTION & QUERY SAFETY
# ============================================================================

def detect_sql_injection_patterns(value):
    """
    Detect common SQL injection patterns in input
    NOTE: This is a defense-in-depth measure. Using Django ORM is the primary defense.
    """
    if not isinstance(value, str):
        return False
    
    value_lower = value.lower()
    
    # Common SQL injection patterns
    sql_patterns = [
        r'(\bor\b.*\b1\b.*=.*\b1\b)',  # OR 1=1
        r'(\bunion\b)',                   # UNION attacks
        r'(\bselect\b)',                  # SELECT
        r'(\binsert\b)',                  # INSERT
        r'(\bupdate\b)',                  # UPDATE
        r'(\bdelete\b)',                  # DELETE
        r'(\bdrop\b)',                    # DROP
        r'(\bexec\b)',                    # EXEC (SQL Server)
        r'(\bexecute\b)',                 # EXECUTE
        r'(-{2,})',                       # SQL comments (--)
        r'(/\*.*?\*/)',                   # SQL comments (/* */)
        r'(;\s*drop)',                    # Stacked queries
        r'(xp_)',                         # Extended stored procedures
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, value_lower):
            logger.warning(f"Potential SQL injection detected: {value[:50]}")
            raise ValidationError('Input contains invalid characters or patterns')
    
    return False


# ============================================================================
# XSS PROTECTION
# ============================================================================

def sanitize_user_input(value, max_length=None):
    """
    Sanitize user input to prevent XSS attacks
    - Escapes HTML entities
    - Removes suspicious scripts
    - Optionally limits length
    
    NOTE: When displaying in React, text is escaped by default, but this adds another layer
    """
    if not isinstance(value, str):
        return value
    
    # Detect SQL injection
    detect_sql_injection_patterns(value)
    
    # HTML escape all special characters
    sanitized = html.escape(value)
    
    # Remove any script tags that might have slipped through
    sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove event handlers (onclick, onerror, etc.)
    sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
    
    # Optionally limit length
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


# ============================================================================
# PHONE NUMBER VALIDATION
# ============================================================================

def normalize_phone_number(phone_number):
    """
    Normalize Kenyan phone number to international format (254xxxxxxxxx)
    Accepts: 254xxxxxxxxx, 0xxxxxxxxx, +254xxxxxxxxx
    Returns: Normalized format (254xxxxxxxxx)
    
    SECURITY: Only allows alphanumeric + signs, prevents injection
    """
    # Only allow digits and + sign
    phone = re.sub(r'[^\d+]', '', str(phone_number))
    
    # Remove leading +
    phone = phone.lstrip('+')
    
    # Convert local format (0xxxxxxxxx) to international format (254xxxxxxxxx)
    if phone.startswith('0'):
        return '254' + phone[1:]
    else:
        return phone


def validate_phone_number(phone_number):
    """
    Validate and normalize Kenyan phone number format
    Accepts: 254xxxxxxxxx, 0xxxxxxxxx, +254xxxxxxxxx
    Returns: Normalized format (254xxxxxxxxx)
    """
    # First normalize
    phone = normalize_phone_number(phone_number)
    
    # Format: 254 followed by 9 digits (Kenyan number starting with country code)
    if not re.match(r'^254\d{9}$', phone):
        raise ValidationError('Phone number must be in format 254xxxxxxxxx or 0xxxxxxxxx')
    
    return phone


# ============================================================================
# AMOUNT VALIDATION
# ============================================================================

def validate_amount(amount, min_amount=Decimal('1'), max_amount=Decimal('150000')):
    """
    Validate transaction amount
    Default range: 1 KES to 150,000 KES
    
    SECURITY: Rejects non-numeric input, NaN, Infinity
    """
    # Validate input type
    if amount is None:
        raise ValidationError('Amount is required')
    
    try:
        amount_decimal = Decimal(str(amount))
    except:
        raise ValidationError('Amount must be a valid number')
    
    # Reject NaN and Infinity
    if amount_decimal.is_nan() or amount_decimal.is_infinite():
        raise ValidationError('Amount must be a valid number')
    
    # Reject negative
    if amount_decimal < 0:
        raise ValidationError('Amount cannot be negative')
    
    # Check range
    if amount_decimal < min_amount:
        raise ValidationError(f'Amount must be at least {min_amount} KES')
    
    if amount_decimal > max_amount:
        raise ValidationError(f'Amount cannot exceed {max_amount} KES')
    
    # Check decimal places (max 2 for KES)
    if amount_decimal.as_tuple().exponent < -2:
        raise ValidationError('Amount can have maximum 2 decimal places')
    
    return amount_decimal


# ============================================================================
# TEXT FIELD VALIDATION
# ============================================================================

def validate_market_question(question):
    """Validate market question for length, content, and XSS"""
    if not question:
        raise ValidationError('Question is required')
    
    if not isinstance(question, str):
        raise ValidationError('Question must be text')
    
    # Check length
    if len(question) < 10:
        raise ValidationError('Question must be at least 10 characters')
    
    if len(question) > 500:
        raise ValidationError('Question cannot exceed 500 characters')
    
    # Sanitize
    sanitized = sanitize_user_input(question, max_length=500)
    
    # Check for profanity (simple version)
    profanities = ['offensive', 'hate', 'illegal', 'racist', 'sexist']
    question_lower = question.lower()
    
    for word in profanities:
        if word in question_lower:
            raise ValidationError('Question contains inappropriate content')
    
    return sanitized


def validate_description(description, required=False, max_length=1000):
    """Validate description text field"""
    if not description:
        if required:
            raise ValidationError('Description is required')
        return ""
    
    if not isinstance(description, str):
        raise ValidationError('Description must be text')
    
    if len(description) > max_length:
        raise ValidationError(f'Description cannot exceed {max_length} characters')
    
    return sanitize_user_input(description, max_length=max_length)


def validate_full_name(full_name):
    """Validate user full name"""
    if not full_name:
        raise ValidationError('Full name is required')
    
    if not isinstance(full_name, str):
        raise ValidationError('Full name must be text')
    
    # Remove extra spaces
    full_name = ' '.join(full_name.split())
    
    if len(full_name) < 2:
        raise ValidationError('Full name must be at least 2 characters')
    
    if len(full_name) > 100:
        raise ValidationError('Full name cannot exceed 100 characters')
    
    # Only allow letters, spaces, hyphens, apostrophes
    if not re.match(r"^[a-zA-Z\s\-']+$", full_name):
        raise ValidationError('Full name can only contain letters, spaces, hyphens, and apostrophes')
    
    return sanitize_user_input(full_name, max_length=100)


def validate_email(email):
    """Validate email address"""
    if not email:
        raise ValidationError('Email is required')
    
    # Simple email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError('Invalid email address')
    
    if len(email) > 254:  # RFC 5321
        raise ValidationError('Email is too long')
    
    return email.lower()


# ============================================================================
# BET & OUTCOME VALIDATION
# ============================================================================

def validate_bet_outcome(outcome):
    """Validate bet outcome"""
    if not outcome:
        raise ValidationError('Outcome is required')
    
    # Only allow exact matches
    valid_outcomes = ['Yes', 'No']
    if outcome not in valid_outcomes:
        raise ValidationError(f'Outcome must be one of: {", ".join(valid_outcomes)}')
    
    return outcome


def validate_bet_amount(amount, user_balance):
    """
    Validate bet amount against user balance
    User cannot bet more than their current balance
    """
    amount_decimal = validate_amount(amount, min_amount=Decimal('1'), max_amount=Decimal('150000'))
    
    if amount_decimal > user_balance:
        raise ValidationError(f'Insufficient balance. Current balance: {user_balance} KES')
    
    return amount_decimal


# ============================================================================
# MARKET CATEGORY VALIDATION
# ============================================================================

def validate_market_category(category):
    """Validate market category"""
    valid_categories = [
        'Sports', 'Politics', 'Economy', 'Crypto', 
        'Environment', 'Technology', 'Entertainment', 'Other'
    ]
    
    if category not in valid_categories:
        raise ValidationError(f'Invalid category. Must be one of: {", ".join(valid_categories)}')
    
    return category
    
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


def validate_password(password):
    """Validate user password"""
    password = str(password)
    
    if len(password) < 6:
        raise ValidationError('Password must be at least 6 characters')
    
    if len(password) > 128:
        raise ValidationError('Password cannot exceed 128 characters')
    
    return password


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
