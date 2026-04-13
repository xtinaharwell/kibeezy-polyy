"""
Audit Trail & Immutability Models

Stores immutable audit logs of all financial operations and data changes.
Ensures complete traceability and tamper detection.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import json
import hashlib


class AuditLog(models.Model):
    """
    Immutable audit log for tracking all important changes.
    
    Features:
    - Automatically tracks who changed what and when
    - Stores before/after values
    - Calculates cryptographic hash for tamper detection
    - Linked to previous log for chain validation
    - Never updated or deleted (immutable)
    """
    
    ACTION_CHOICES = [
        ('CREATE', 'Record Created'),
        ('UPDATE', 'Record Updated'),
        ('DELETE', 'Record Deleted'),
        ('DEPOSIT', 'Deposit Processed'),
        ('WITHDRAWAL', 'Withdrawal Processed'),
        ('BET_PLACED', 'Bet Placed'),
        ('MARKET_RESOLVED', 'Market Resolved'),
        ('PAYOUT_ISSUED', 'Payout Issued'),
        ('BALANCE_ADJUSTED', 'Balance Adjusted'),
        ('PERMISSION_CHANGED', 'Permission Changed'),
        ('LOGIN', 'User Login'),
        ('KYC_VERIFIED', 'KYC Verified'),
        ('ADMIN_ACTION', 'Admin Action'),
        ('SYSTEM_ACTION', 'System Action'),
    ]
    
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    # What happened
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='MEDIUM')
    
    # What was affected
    content_type = models.CharField(max_length=255)  # e.g., 'payments.Transaction'
    object_id = models.CharField(max_length=255)  # ID of changed record
    object_repr = models.TextField()  # String representation of object
    
    # Who did it
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, 
                            related_name='audit_logs_created', null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # What changed
    changes = models.JSONField(default=dict, blank=True)  # {field: {old: ..., new: ...}}
    before_values = models.JSONField(default=dict, blank=True)
    after_values = models.JSONField(default=dict, blank=True)
    
    # Timestamps (immutable)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Cryptographic integrity
    previous_hash = models.CharField(max_length=256, null=True, blank=True)
    current_hash = models.CharField(max_length=256, unique=True)
    hash_verified = models.BooleanField(default=False)
    
    # Metadata
    description = models.TextField(blank=True)
    related_transaction = models.CharField(max_length=255, blank=True)  # e.g., txn_id
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['object_id', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
            models.Index(fields=['created_at']),  # Timeline queries
        ]
        permissions = [
            ('view_audit_logs', 'Can view audit logs'),
            ('export_audit_logs', 'Can export audit logs'),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.content_type}:{self.object_id} by {self.user or 'system'}"
    
    def calculate_hash(self, previous_hash=''):
        """
        Calculate SHA256 hash of this record for integrity verification.
        
        Hash includes:
        - Previous hash (creating a chain)
        - Action, content_type, object_id
        - Changes made
        - Timestamp
        - User
        
        This ensures tampering can be detected.
        """
        hash_input = f"{previous_hash}|{self.action}|{self.content_type}|{self.object_id}|{json.dumps(self.changes, sort_keys=True)}|{self.created_at.isoformat()}|{self.user_id or ''}"
        
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def verify_hash(self):
        """
        Verify that this record hasn't been tampered with.
        
        Returns True if:
        - Calculated hash matches stored hash
        - Optional: Previous hash matches previous record's hash (chain validation)
        """
        calculated = self.calculate_hash(self.previous_hash or '')
        
        if calculated != self.current_hash:
            return False
        
        # Verify chain if previous_hash exists
        if self.previous_hash:
            try:
                prev_log = AuditLog.objects.get(current_hash=self.previous_hash)
                if not prev_log.hash_verified:
                    # Previous record tampered with
                    return False
            except AuditLog.DoesNotExist:
                # Previous hash doesn't exist - corruption detected
                return False
        
        return True
    
    def save(self, *args, **kwargs):
        """Override save to ensure immutability and hash calculation"""
        
        # Prevent updates to existing records
        if self.pk is not None:
            # Allow only specific fields for initial metadata
            raise ValueError(
                "AuditLog records are immutable. "
                "Cannot update existing audit log entry."
            )
        
        # Ensure created_at is set before hashing (auto_now_add won't set it until super().save())
        if not self.created_at:
            self.created_at = timezone.now()
        
        # Calculate hash if not already set
        if not self.current_hash:
            # Get previous record's hash for chain
            try:
                prev_log = AuditLog.objects.latest('created_at')
                self.previous_hash = prev_log.current_hash
            except AuditLog.DoesNotExist:
                self.previous_hash = ''
            
            self.current_hash = self.calculate_hash(self.previous_hash or '')
            self.hash_verified = self.verify_hash()
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of audit logs"""
        raise ValueError(
            "AuditLog records cannot be deleted. "
            "They are permanent for compliance and audit purposes."
        )


class AuditSummary(models.Model):
    """
    Daily summary of audit activity for quick reporting.
    Helps identify trends and anomalies.
    """
    
    date = models.DateField(db_index=True, unique=True)
    
    # Activity counts
    total_actions = models.IntegerField(default=0)
    creates = models.IntegerField(default=0)
    updates = models.IntegerField(default=0)
    deletes = models.IntegerField(default=0)
    financial_actions = models.IntegerField(default=0)  # Deposits, withdrawals, payouts
    admin_actions = models.IntegerField(default=0)
    
    # Users involved
    unique_users = models.IntegerField(default=0)
    
    # Risk indicators
    critical_count = models.IntegerField(default=0)
    high_count = models.IntegerField(default=0)
    
    # Financial impact
    total_amount_processed = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"Audit Summary - {self.date} ({self.total_actions} actions)"


class AccessLog(models.Model):
    """
    Track who accessed sensitive data for compliance.
    Different from AuditLog - this logs reads, not writes.
    """
    
    RESOURCE_TYPES = [
        ('USER_PROFILE', 'User Profile'),
        ('BALANCE', 'User Balance'),
        ('TRANSACTIONS', 'Transaction History'),
        ('AUDIT_LOGS', 'Audit Logs'),
        ('ADMIN_PANEL', 'Admin Panel'),
        ('REPORTS', 'Reports'),
        ('API_KEY', 'API Key'),
    ]
    
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    resource_id = models.CharField(max_length=255)
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, 
                            related_name='access_logs')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # What they accessed
    query_params = models.JSONField(default=dict, blank=True)
    
    # Result
    status_code = models.IntegerField(default=200)
    success = models.BooleanField(default=True)
    
    # Timestamps
    accessed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-accessed_at']
        indexes = [
            models.Index(fields=['resource_type', '-accessed_at']),
            models.Index(fields=['user', '-accessed_at']),
        ]
    
    def __str__(self):
        return f"{self.user} accessed {self.resource_type}:{self.resource_id}"


class AuditAlert(models.Model):
    """
    Alerts for suspicious audit patterns.
    Automatically generated when anomalies detected.
    """
    
    ALERT_TYPES = [
        ('MULTIPLE_FAILED_LOGINS', 'Multiple Failed Logins'),
        ('UNUSUAL_BALANCE_CHANGE', 'Unusual Balance Change'),
        ('LARGE_WITHDRAWAL', 'Large Withdrawal'),
        ('ADMIN_ACCESS_OUTSIDE_HOURS', 'Admin Access Outside Hours'),
        ('RAPID_TRANSACTIONS', 'Rapid Transactions'),
        ('HASH_VERIFICATION_FAILED', 'Hash Verification Failed'),
        ('BULK_DATA_EXPORT', 'Bulk Data Export'),
        ('PERMISSION_ESCALATION', 'Permission Escalation'),
        ('DUPLICATE_TRANSACTION', 'Duplicate Transaction'),
    ]
    
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    severity = models.CharField(
        max_length=10,
        choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')],
        default='MEDIUM'
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                            related_name='audit_alerts', null=True, blank=True)
    
    description = models.TextField()
    related_logs = models.JSONField(default=list)  # IDs of related AuditLog records
    
    # Status
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                       related_name='alerts_acknowledged', null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Investigation
    notes = models.TextField(blank=True)
    action_taken = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['severity', '-created_at']),
            models.Index(fields=['acknowledged', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.alert_type} - {self.severity}"
    
    def acknowledge(self, user, notes=''):
        """Mark alert as acknowledged by admin"""
        self.acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.notes = notes
        self.save()
