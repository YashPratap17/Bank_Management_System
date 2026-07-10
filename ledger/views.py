# pyrefly: ignore [missing-import]
from django.contrib import messages
# pyrefly: ignore [missing-import]
from django.contrib.auth.decorators import login_required
# pyrefly: ignore [missing-import]
from django.http import JsonResponse
# pyrefly: ignore [missing-import]
from django.shortcuts import render, redirect
from django.http import HttpResponse
# pyrefly: ignore [missing-import]
from django.views.decorators.http import require_GET

# pyrefly: ignore [missing-import]
from .forms import AmountForm, TransferForm
# pyrefly: ignore [missing-import]
from .services import deposit, withdraw, transfer, InsufficientFundsError, AccountNotActiveError
# pyrefly: ignore [missing-import]
from accounts.models import Account


def _get_active_customer_account(request):
    """Every view here needs the same guard: logged in, approved, has an account."""
    customer = getattr(request.user, "customer", None)
    if customer is None or not customer.is_approved():
        return None
    return customer.accounts.first()


@login_required
def deposit_view(request):
    account = _get_active_customer_account(request)
    if account is None:
        return redirect("dashboard:home")

    if request.method == "POST":
        form = AmountForm(request.POST)
        if form.is_valid():
            try:
                deposit(account, form.cleaned_data["amount"], form.cleaned_data["description"])
                messages.success(request, f"Deposited Rs.{form.cleaned_data['amount']}.")
                return redirect("dashboard:home")
            except AccountNotActiveError as e:
                messages.error(request, str(e))
    else:
        form = AmountForm()
    return render(request, "ledger/deposit.html", {"form": form, "account": account})


@login_required
def withdraw_view(request):
    account = _get_active_customer_account(request)
    if account is None:
        return redirect("dashboard:home")

    if request.method == "POST":
        form = AmountForm(request.POST)
        if form.is_valid():
            try:
                withdraw(account, form.cleaned_data["amount"], form.cleaned_data["description"])
                messages.success(request, f"Withdrew Rs.{form.cleaned_data['amount']}.")
                return redirect("dashboard:home")
            except InsufficientFundsError as e:
                messages.error(request, str(e))
            except AccountNotActiveError as e:
                messages.error(request, str(e))
    else:
        form = AmountForm()
    return render(request, "ledger/withdraw.html", {"form": form, "account": account})


@login_required
def transfer_view(request):
    account = _get_active_customer_account(request)
    if account is None:
        return redirect("dashboard:home")

    if request.method == "POST":
        form = TransferForm(request.POST, sender_account=account)
        if form.is_valid():
            recipient_account = form.cleaned_data["recipient_account"]
            try:
                transfer(
                    account, 
                    recipient_account, 
                    form.cleaned_data["amount"], 
                    form.cleaned_data["description"],
                    category=form.cleaned_data.get("category", "AUTO")
                )
                messages.success(
                    request,
                    f"Sent Rs.{form.cleaned_data['amount']} to {recipient_account.customer.full_name} "
                    f"({recipient_account.account_number})."
                )
                return redirect("dashboard:home")
            except InsufficientFundsError as e:
                messages.error(request, str(e))
            except AccountNotActiveError as e:
                messages.error(request, str(e))
    else:
        form = TransferForm(sender_account=account)
    return render(request, "ledger/transfer.html", {"form": form, "account": account})


@login_required
def history_view(request):
    account = _get_active_customer_account(request)
    if account is None:
        return redirect("dashboard:home")
        
    from .models import LedgerEntry
    entries = LedgerEntry.objects.filter(account=account).select_related("transaction").order_by("-created_at")[:500]
    return render(request, "ledger/history.html", {"account": account, "entries": entries})


@login_required
def download_statement_view(request):
    import csv
    account = _get_active_customer_account(request)
    if account is None:
        return redirect("dashboard:home")
        
    from .models import LedgerEntry
    entries = LedgerEntry.objects.filter(account=account).select_related("transaction").order_by("-created_at")
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="statement_{account.account_number}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Description', 'Category', 'Type', 'Amount', 'Balance After'])
    
    for entry in entries:
        writer.writerow([
            entry.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            entry.transaction.description,
            entry.transaction.category,
            entry.entry_type,
            entry.amount,
            entry.balance_after
        ])
        
    return response


@require_GET
@login_required
def account_lookup(request):
    """
    JSON endpoint: given ?roll=<account_number>, return recipient name or error.
    Case‑insensitive match, active accounts only.
    """
    roll = request.GET.get("roll", "").strip().upper()
    if not roll:
        return JsonResponse({"found": False, "error": "No account number provided."})

    # Don't reveal info about your own account
    sender = _get_active_customer_account(request)
    try:
        acc = Account.objects.select_related("customer").get(
            account_number__iexact=roll,
            status=Account.Status.ACTIVE,
        )
        if sender and acc.pk == sender.pk:
            return JsonResponse({"found": False, "error": "That's your own account."})

        return JsonResponse({
            "found": True,
            "name": acc.customer.full_name,
            "branch": acc.customer.branch or "",
            "account_number": acc.account_number,
        })
    except Account.DoesNotExist:
        return JsonResponse({"found": False, "error": "No active account found with this number."})