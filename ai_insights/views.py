from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Customer, Card
from ledger.models import Transaction
from ledger.services import deposit
from decimal import Decimal


@staff_member_required
def risk_dashboard(request):
    flagged = (
        Transaction.objects
        .filter(status=Transaction.Status.FLAGGED)
        .prefetch_related("entries__account__customer")
        .order_by("-ai_risk_score", "-created_at")
    )
    high_score_unflagged = (
        Transaction.objects
        .exclude(status=Transaction.Status.FLAGGED)
        .filter(ai_risk_score__gte=0.3)
        .prefetch_related("entries__account__customer")
        .order_by("-ai_risk_score")[:20]
    )
    return render(request, "ai_insights/risk_dashboard.html", {
        "flagged": flagged,
        "watchlist": high_score_unflagged,
    })


@staff_member_required
def approvals_dashboard(request):
    pending = Customer.objects.filter(
        approval_status=Customer.ApprovalStatus.PENDING
    ).select_related("user").order_by("created_at")
    recently_decided = Customer.objects.exclude(
        approval_status=Customer.ApprovalStatus.PENDING
    ).select_related("user", "approved_by").order_by("-approved_at")[:20]
    
    pending_cards = Card.objects.filter(status=Card.Status.PENDING_APPROVAL).select_related("account__customer")

    return render(request, "ai_insights/approvals_dashboard.html", {
        "pending": pending,
        "recently_decided": recently_decided,
        "pending_cards": pending_cards,
    })


@staff_member_required
@require_POST
def approve_customer(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    customer.approval_status = Customer.ApprovalStatus.APPROVED
    customer.approved_by = request.user
    customer.approved_at = timezone.now()
    customer.save()

    # Provide 5000 opening balance to any new accounts
    for account in customer.accounts.all():
        if account.get_balance() == 0:
            deposit(account, Decimal("5000.00"), "Welcome Bonus")
        
        # Issue a Debit Card automatically
        if not account.cards.filter(card_type=Card.CardType.DEBIT).exists():
            Card.objects.create(account=account, card_type=Card.CardType.DEBIT, status=Card.Status.ACTIVE)

    messages.success(request, f"Approved {customer.full_name} ({customer.roll_number}).")
    return redirect("ai_insights:approvals_dashboard")


@staff_member_required
@require_POST
def reject_customer(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    customer.approval_status = Customer.ApprovalStatus.REJECTED
    customer.approved_by = request.user
    customer.approved_at = timezone.now()
    customer.save()
    messages.warning(request, f"Rejected {customer.full_name} ({customer.roll_number}).")
    return redirect("ai_insights:approvals_dashboard")


@staff_member_required
@require_POST
def approve_card(request, card_id):
    card = get_object_or_404(Card, pk=card_id)
    card.status = Card.Status.ACTIVE
    card.save()
    messages.success(request, f"Approved Credit Card for {card.account.customer.full_name}.")
    return redirect("ai_insights:approvals_dashboard")


@staff_member_required
@require_POST
def reject_card(request, card_id):
    card = get_object_or_404(Card, pk=card_id)
    card.status = Card.Status.REJECTED
    card.save()
    messages.warning(request, f"Rejected Credit Card for {card.account.customer.full_name}.")
    return redirect("ai_insights:approvals_dashboard")
