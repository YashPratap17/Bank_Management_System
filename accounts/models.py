# import json
# import uuid
# import base64
# import re

# from django.conf import settings
# from django.core.exceptions import ValidationError
# from django.db import models
# from cryptography.fernet import Fernet


# def get_fernet():
#     # Derive a stable key from SECRET_KEY (must be exactly 32 url-safe base64 bytes)
#     secret = settings.SECRET_KEY
#     key = base64.urlsafe_b64encode(secret[:32].encode().ljust(32, b'='))
#     return Fernet(key)


# def validate_roll_number(value):
#     if not re.match(r'^[A-Za-z0-9]+$', value):
#         raise ValidationError("Roll number must contain only letters and digits.")


# class Customer(models.Model):
#     class ApprovalStatus(models.TextChoices):
#         PENDING  = "PENDING",  "Pending approval"
#         APPROVED = "APPROVED", "Approved"
#         REJECTED = "REJECTED", "Rejected"

#     user            = models.OneToOneField(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name="customer",
#     )
#     full_name       = models.CharField(max_length=150)
#     roll_number     = models.CharField(
#         max_length=20,
#         unique=True,
#         validators=[validate_roll_number],
#         help_text="Used as this student's account number.",
#     )
#     branch          = models.CharField(max_length=50, blank=True)
#     phone_number    = models.CharField(max_length=15, blank=True)
#     approval_status = models.CharField(
#         max_length=10,
#         choices=ApprovalStatus.choices,
#         default=ApprovalStatus.PENDING,
#     )
#     approved_by     = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.SET_NULL,
#         null=True, blank=True,
#         related_name="approved_customers",
#     )
#     approved_at     = models.DateTimeField(null=True, blank=True)
#     created_at      = models.DateTimeField(auto_now_add=True)

#     def is_approved(self):
#         return self.approval_status == self.ApprovalStatus.APPROVED

#     def __str__(self):
#         return f"{self.full_name} ({self.roll_number})"


# class Account(models.Model):
#     class AccountType(models.TextChoices):
#         SAVINGS = "SAVINGS", "Savings"
#         CURRENT = "CURRENT", "Current"

#     class Status(models.TextChoices):
#         ACTIVE = "ACTIVE", "Active"
#         FROZEN = "FROZEN", "Frozen"
#         CLOSED = "CLOSED", "Closed"

#     account_number = models.CharField(max_length=20, unique=True, editable=False)
#     customer       = models.ForeignKey(
#         Customer,
#         on_delete=models.PROTECT,
#         related_name="accounts",
#     )
#     account_type   = models.CharField(
#         max_length=10,
#         choices=AccountType.choices,
#         default=AccountType.SAVINGS,
#     )
#     status         = models.CharField(
#         max_length=10,
#         choices=Status.choices,
#         default=Status.ACTIVE,
#     )
#     opened_at      = models.DateTimeField(auto_now_add=True)

#     def save(self, *args, **kwargs):
#         # Always use the customer's roll number as the account number
#         if not self.customer_id:
#             raise ValidationError("Account must be linked to a customer.")
#         roll = self.customer.roll_number
#         if not roll:
#             raise ValidationError("Customer has no roll number — cannot create account.")
#         self.account_number = roll
#         super().save(*args, **kwargs)

#     def get_balance(self):
#         from ledger.models import LedgerEntry
#         from django.db.models import Sum
#         credits = (
#             LedgerEntry.objects
#             .filter(account=self, entry_type=LedgerEntry.EntryType.CREDIT)
#             .aggregate(total=Sum("amount"))["total"] or 0
#         )
#         debits = (
#             LedgerEntry.objects
#             .filter(account=self, entry_type=LedgerEntry.EntryType.DEBIT)
#             .aggregate(total=Sum("amount"))["total"] or 0
#         )
#         return credits - debits

#     def __str__(self):
#         return f"{self.account_number} ({self.customer.full_name})"


# class FaceProfile(models.Model):
#     user = models.OneToOneField(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name='face_profile'
#     )
#     encrypted_descriptor = models.BinaryField()  # AES-encrypted 128-float array
#     created_at = models.DateTimeField(auto_now_add=True)

#     def set_descriptor(self, descriptor_list):
#         """descriptor_list: list of 128 floats from face-api"""
#         json_str = json.dumps(descriptor_list)
#         f = get_fernet()
#         self.encrypted_descriptor = f.encrypt(json_str.encode())

#     def get_descriptor(self):
#         f = get_fernet()
#         decrypted = f.decrypt(self.encrypted_descriptor)
#         return json.loads(decrypted)

#     def __str__(self):
#         return f"FaceProfile for {self.user.username}"


import json
import os
import uuid
import base64
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from cryptography.fernet import Fernet


def get_fernet():
    """
    Build a stable Fernet key for encrypting face descriptors.

    Priority:
      1. FACE_ENCRYPTION_KEY env var — a raw 32-byte value used as a stable,
         environment-independent key.  Set this on Render (and locally) so
         that descriptors registered in one environment can be verified in
         another.  Generate once with:
             python -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
         then store the output as the FACE_ENCRYPTION_KEY env var.
      2. SECRET_KEY fallback — works for single-environment dev, but will
         break cross-environment decryption if SECRET_KEY differs.
    """
    raw_key = os.environ.get('FACE_ENCRYPTION_KEY')
    if raw_key:
        # Ensure the key is properly padded url-safe base64 (Fernet requires
        # exactly 32 bytes of key material encoded as url-safe base64).
        key = raw_key.encode() if isinstance(raw_key, str) else raw_key
    else:
        # Fallback: derive from SECRET_KEY (same environment only)
        secret = settings.SECRET_KEY
        key = base64.urlsafe_b64encode(secret[:32].encode().ljust(32, b'='))
    return Fernet(key)


def validate_roll_number(value):
    if not re.match(r'^[A-Za-z0-9]+$', value):
        raise ValidationError("Roll number must contain only letters and digits.")


class Customer(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING  = "PENDING",  "Pending approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    user            = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer",
    )
    full_name       = models.CharField(max_length=150)
    roll_number     = models.CharField(
        max_length=20,
        unique=True,
        validators=[validate_roll_number],
        help_text="Used as this student's account number.",
    )
    branch          = models.CharField(max_length=50, blank=True)
    phone_number    = models.CharField(max_length=15, blank=True)
    approval_status = models.CharField(
        max_length=10,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    approved_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="approved_customers",
    )
    approved_at     = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def is_approved(self):
        return self.approval_status == self.ApprovalStatus.APPROVED

    def __str__(self):
        return f"{self.full_name} ({self.roll_number})"


class Account(models.Model):
    class AccountType(models.TextChoices):
        SAVINGS = "SAVINGS", "Savings"
        CURRENT = "CURRENT", "Current"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        FROZEN = "FROZEN", "Frozen"
        CLOSED = "CLOSED", "Closed"

    account_number = models.CharField(max_length=20, unique=True, editable=False)
    customer       = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    account_type   = models.CharField(
        max_length=10,
        choices=AccountType.choices,
        default=AccountType.SAVINGS,
    )
    status         = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    opened_at      = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Always use the customer's roll number as the account number
        if not self.customer_id:
            raise ValidationError("Account must be linked to a customer.")
        roll = self.customer.roll_number
        if not roll:
            raise ValidationError("Customer has no roll number — cannot create account.")
        self.account_number = roll
        super().save(*args, **kwargs)

    def get_balance(self):
        from ledger.models import LedgerEntry
        from django.db.models import Sum
        credits = (
            LedgerEntry.objects
            .filter(account=self, entry_type=LedgerEntry.EntryType.CREDIT)
            .aggregate(total=Sum("amount"))["total"] or 0
        )
        debits = (
            LedgerEntry.objects
            .filter(account=self, entry_type=LedgerEntry.EntryType.DEBIT)
            .aggregate(total=Sum("amount"))["total"] or 0
        )
        return credits - debits

    def __str__(self):
        return f"{self.account_number} ({self.customer.full_name})"


class FaceProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='face_profile'
    )
    encrypted_descriptor = models.BinaryField()  # AES-encrypted 128-float array
    created_at = models.DateTimeField(auto_now_add=True)

    def set_descriptor(self, descriptor_list):
        """descriptor_list: list of 128 floats from face-api"""
        json_str = json.dumps(descriptor_list)
        f = get_fernet()
        self.encrypted_descriptor = f.encrypt(json_str.encode())

    def get_descriptor(self):
        f = get_fernet()
        # Ensure we have raw bytes (PostgreSQL returns memoryview)
        encrypted_bytes = bytes(self.encrypted_descriptor)
        decrypted = f.decrypt(encrypted_bytes)
        return json.loads(decrypted)

    def __str__(self):
        return f"FaceProfile for {self.user.username}"