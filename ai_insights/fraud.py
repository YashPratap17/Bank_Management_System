"""
Rule-based fraud/anomaly scoring.

Deliberately NOT machine learning to start with — a bank's real fraud
systems layer many simple rules before any ML model, because rules are
auditable ("why was this flagged?") in a way a black-box model isn't.
Score is in [0, 1]. Each rule contributes independently and explains itself
via `reasons`, which the Risk Dashboard displays to staff.

If you have time later, IsolationForest from scikit-learn can sit on top
of these same features (amount, z-score, hour) — but this rule-based layer
should keep working even if that's never added.
"""
from statistics import mean, pstdev
from django.utils import timezone

ODD_HOUR_START, ODD_HOUR_END = 0, 5  # 12:00 AM - 5:59 AM
HIGH_RISK_THRESHOLD = 0.6
HISTORY_WINDOW = 60  # look at the last N same-direction entries for this account


def score_transaction(account, entry_type, amount, created_at=None):
    """
    Returns (score: float, reasons: list[str]).

    account: the Account being debited/credited
    entry_type: LedgerEntry.EntryType.DEBIT or .CREDIT
    amount: Decimal amount of this specific movement
    created_at: datetime to evaluate "odd hour" against (defaults to now)
    """
    from ledger.models import LedgerEntry  # local import: avoids ai_insights <-> ledger cycle

    created_at = created_at or timezone.now()
    reasons = []
    score = 0.0

    past_entries = (
        LedgerEntry.objects
        .filter(account=account, entry_type=entry_type)
        .order_by("-created_at")[:HISTORY_WINDOW]
    )
    amounts = [float(e.amount) for e in past_entries]

    if len(amounts) >= 5:
        avg = mean(amounts)
        std = pstdev(amounts) or 1.0
        z = (float(amount) - avg) / std
        if z > 3:
            score += 0.6
            reasons.append(f"Amount is {z:.1f} standard deviations above this account's typical {entry_type.lower()}")
        elif z > 2:
            score += 0.35
            reasons.append(f"Amount is unusually high ({z:.1f} std deviations above average)")
    else:
        # Not enough history yet to judge statistically — fall back to a
        # flat large-amount threshold rather than staying silent.
        if float(amount) > 30000:
            score += 0.3
            reasons.append("Large amount with limited account history to compare against")

    if ODD_HOUR_START <= created_at.hour <= ODD_HOUR_END:
        score += 0.3
        reasons.append(f"Transaction occurred at an unusual hour ({created_at.hour:02d}:00)")

    score = min(score, 1.0)
    return score, reasons
