"""
All money movement goes through this file. Views should never touch
LedgerEntry.objects.create() directly — always go through these functions,
so there's exactly one place that can create a debit/credit pair, and
exactly one place to add a fraud check hook later.
"""
from decimal import Decimal
from django.db import transaction as db_transaction

from django.db.models import Sum, Case, When, F, DecimalField

from accounts.models import Account
from .models import Transaction, LedgerEntry
from .utils.categorizer import categorize_transaction
from ai_insights.fraud import score_transaction, HIGH_RISK_THRESHOLD


class InsufficientFundsError(Exception):
    pass


class AccountNotActiveError(Exception):
    pass


def get_balance(account: Account) -> Decimal:
    """
    The ONLY source of truth for an account's balance.
    Computed live from the ledger — never read a cached field for this.
    """
    result = LedgerEntry.objects.filter(account=account).aggregate(
        balance=Sum(
            Case(
                When(entry_type=LedgerEntry.EntryType.CREDIT, then=F("amount")),
                When(entry_type=LedgerEntry.EntryType.DEBIT, then=-F("amount")),
                output_field=DecimalField(),
            )
        )
    )
    return result["balance"] or Decimal("0.00")


def _assert_active(account: Account):
    if account.status != Account.Status.ACTIVE:
        raise AccountNotActiveError(f"Account {account.account_number} is {account.status}, not active.")


def _apply_fraud_score(tx: Transaction, account: Account, entry_type: str, amount: Decimal):
    """
    Scores a transaction against the account's own history and flags it if
    the score crosses HIGH_RISK_THRESHOLD. Runs synchronously for now — at
    real scale this would move to a Celery task so it doesn't add latency
    to the request, but for this project's volume it's instant either way.
    """
    score, reasons = score_transaction(account, entry_type, amount, created_at=tx.created_at)
    tx.ai_risk_score = score
    tx.ai_risk_reasons = reasons
    if score >= HIGH_RISK_THRESHOLD:
        tx.status = Transaction.Status.FLAGGED
    tx.save(update_fields=["ai_risk_score", "ai_risk_reasons", "status"])


@db_transaction.atomic
def deposit(account: Account, amount: Decimal, description: str = "") -> Transaction:
    _assert_active(account)
    if amount <= 0:
        raise ValueError("Deposit amount must be positive.")

    category = categorize_transaction(description)
    tx = Transaction.objects.create(
        tx_type=Transaction.TxType.DEPOSIT,
        description=description,
        category=category,
    )
    new_balance = get_balance(account) + amount
    LedgerEntry.objects.create(
        transaction=tx, account=account,
        entry_type=LedgerEntry.EntryType.CREDIT,
        amount=amount, balance_after=new_balance,
    )
    _apply_fraud_score(tx, account, LedgerEntry.EntryType.CREDIT, amount)
    return tx


@db_transaction.atomic
def withdraw(account: Account, amount: Decimal, description: str = "") -> Transaction:
    _assert_active(account)
    if amount <= 0:
        raise ValueError("Withdrawal amount must be positive.")

    current_balance = get_balance(account)
    if current_balance < amount:
        raise InsufficientFundsError(
            f"Insufficient funds: balance {current_balance}, requested {amount}."
        )

    category = categorize_transaction(description)
    tx = Transaction.objects.create(
        tx_type=Transaction.TxType.WITHDRAW,
        description=description,
        category=category,
    )
    new_balance = current_balance - amount
    LedgerEntry.objects.create(
        transaction=tx, account=account,
        entry_type=LedgerEntry.EntryType.DEBIT,
        amount=amount, balance_after=new_balance,
    )
    _apply_fraud_score(tx, account, LedgerEntry.EntryType.DEBIT, amount)
    return tx


@db_transaction.atomic
def transfer(from_account: Account, to_account: Account, amount: Decimal, description: str = "") -> Transaction:
    if from_account.pk == to_account.pk:
        raise ValueError("Cannot transfer to the same account.")
    _assert_active(from_account)
    _assert_active(to_account)
    if amount <= 0:
        raise ValueError("Transfer amount must be positive.")

    from_balance = get_balance(from_account)
    if from_balance < amount:
        raise InsufficientFundsError(
            f"Insufficient funds: balance {from_balance}, requested {amount}."
        )

    # Include the recipient's name/account in categorization context so
    # keywords in the recipient field (e.g. "Zomato") are also matched.
    recipient_str = str(to_account.customer.full_name)
    category = categorize_transaction(description, recipient=recipient_str)
    tx = Transaction.objects.create(
        tx_type=Transaction.TxType.TRANSFER,
        description=description,
        category=category,
    )

    new_from_balance = from_balance - amount
    LedgerEntry.objects.create(
        transaction=tx, account=from_account,
        entry_type=LedgerEntry.EntryType.DEBIT,
        amount=amount, balance_after=new_from_balance,
    )

    new_to_balance = get_balance(to_account) + amount
    LedgerEntry.objects.create(
        transaction=tx, account=to_account,
        entry_type=LedgerEntry.EntryType.CREDIT,
        amount=amount, balance_after=new_to_balance,
    )

    # Score the debit side — the money-leaving leg is the higher-relevance
    # side for fraud (an account suddenly losing money matters more than
    # one suddenly receiving it, in this context).
    _apply_fraud_score(tx, from_account, LedgerEntry.EntryType.DEBIT, amount)

    return tx
