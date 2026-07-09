import uuid
# pyrefly: ignore [missing-import]
from django.db import models
# pyrefly: ignore [missing-import]
from django.core.exceptions import ValidationError

from accounts.models import Account


class Transaction(models.Model):
    """
    One 'event' — a deposit, withdrawal, or transfer. A single Transaction
    can produce one LedgerEntry (deposit/withdraw) or two (transfer: a debit
    on one account, a credit on another). This is what lets us do proper
    double-entry style bookkeeping instead of a single balance mutation.
    """

    class TxType(models.TextChoices):
        DEPOSIT = "DEPOSIT", "Deposit"
        WITHDRAW = "WITHDRAW", "Withdraw"
        TRANSFER = "TRANSFER", "Transfer"

    class Status(models.TextChoices):
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        FLAGGED = "FLAGGED", "Flagged"  # completed, but AI fraud check raised a concern

    class Category(models.TextChoices):
        FOOD = "Food", "Food"
        TRANSPORT = "Transport", "Transport"
        SHOPPING = "Shopping", "Shopping"
        ENTERTAINMENT = "Entertainment", "Entertainment"
        BILLS = "Bills", "Bills"
        EDUCATION = "Education", "Education"
        OTHER = "Other", "Other"

    reference_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tx_type = models.CharField(max_length=10, choices=TxType.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.COMPLETED)
    description = models.CharField(max_length=255, blank=True)
    category = models.CharField(
        max_length=30, choices=Category.choices, default="Other"
    )  # auto-filled by keyword categorizer
    ai_risk_score = models.FloatField(null=True, blank=True)  # filled by fraud model
    ai_risk_reasons = models.JSONField(default=list, blank=True)  # human-readable explanation
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tx_type} [{self.reference_id}]"


class LedgerEntry(models.Model):
    """
    THE CORE TABLE. Immutable — rows are never updated after creation, only
    inserted. Balance is always SUM(CREDIT) - SUM(DEBIT) for an account,
    computed on demand (see services.get_balance). Never trust a cached
    number over this table.
    """

    class EntryType(models.TextChoices):
        DEBIT = "DEBIT", "Debit"    # money leaving the account
        CREDIT = "CREDIT", "Credit"  # money entering the account

    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT, related_name="entries")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="ledger_entries")
    entry_type = models.CharField(max_length=6, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)  # snapshot for fast reads
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("LedgerEntry rows are immutable and cannot be edited.")
        if self.amount <= 0:
            raise ValidationError("Ledger amounts must be positive; direction is set by entry_type.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("LedgerEntry rows cannot be deleted. Reverse with a new entry instead.")

    def __str__(self):
        return f"{self.entry_type} {self.amount} -> {self.account.account_number}"
