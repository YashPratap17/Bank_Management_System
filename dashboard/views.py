import json
from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from accounts.models import Customer, Account
from accounts.forms import StudentRegistrationForm
from ledger.models import LedgerEntry, Transaction


def landing_or_dashboard(request):
    if request.user.is_authenticated:
        return dashboard_home(request)
    return render(request, "dashboard/landing.html")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = User.objects.create_user(
                username=data["roll_number"],
                password=data["password"],
                first_name=data["full_name"].split(" ")[0],
            )
            customer = Customer.objects.create(
                user=user,
                full_name=data["full_name"],
                roll_number=data["roll_number"],
                branch=data.get("branch", ""),
                approval_status=Customer.ApprovalStatus.PENDING,
            )
            Account.objects.create(customer=customer, account_type=Account.AccountType.SAVINGS)
            login(request, user)
            return redirect("dashboard:register_face")
    else:
        form = StudentRegistrationForm()
    return render(request, "dashboard/register.html", {"form": form})


def dashboard_home(request):
    if not request.user.is_authenticated:
        return redirect("login")
    customer = getattr(request.user, "customer", None)
    if customer is None:
        return render(request, "dashboard/no_profile.html")

    if not customer.is_approved():
        return render(request, "dashboard/pending_approval.html", {"customer": customer})

    accounts = customer.accounts.all()
    account = accounts.first()

    # ── Mini chart data for dashboard ──────────────────────────────
    category_labels = json.dumps([])
    category_data   = json.dumps([])
    balance_dates   = json.dumps([])
    balance_values  = json.dumps([])
    account_stats   = {"total_in": "0.00", "total_out": "0.00"}
    spend_pct       = 0
    category_data_zipped = []

    if account:
        # Spend by category (debit entries)
        from ledger.models import LedgerEntry
        debit_entries = (
            LedgerEntry.objects
            .filter(account=account, entry_type=LedgerEntry.EntryType.DEBIT)
            .select_related("transaction")
        )
        credit_entries = (
            LedgerEntry.objects
            .filter(account=account, entry_type=LedgerEntry.EntryType.CREDIT)
        )

        cat_totals: dict[str, Decimal] = defaultdict(Decimal)
        total_out = Decimal("0")
        for e in debit_entries:
            cat_totals[e.transaction.category or "Other"] += e.amount
            total_out += e.amount

        total_in = Decimal("0")
        for e in credit_entries:
            total_in += e.amount

        category_labels = json.dumps(list(cat_totals.keys()))
        cat_values = [float(v) for v in cat_totals.values()]
        category_data = json.dumps(cat_values)
        category_data_zipped = list(zip(cat_totals.keys(), cat_totals.values()))

        account_stats = {
            "total_in":  f"{total_in:.2f}",
            "total_out": f"{total_out:.2f}",
        }
        total_flow = total_in + total_out
        spend_pct = int((total_out / total_flow) * 100) if total_flow else 0

        # Attach recent ledger entries to each account for template iteration
        for acc in accounts:
            acc.recent_entries = (
                LedgerEntry.objects
                .filter(account=acc)
                .select_related("transaction")
                .order_by("-created_at")[:10]
            )

        # Daily balance history
        all_entries = (
            LedgerEntry.objects
            .filter(account=account)
            .order_by("created_at")
            .values("created_at", "balance_after")
        )
        daily: dict[str, float] = {}
        for e in all_entries:
            dt = e["created_at"]
            if timezone.is_aware(dt):
                dt = timezone.localtime(dt)
            daily[dt.strftime("%Y-%m-%d")] = float(e["balance_after"])
        balance_dates  = json.dumps(list(daily.keys()))
        balance_values = json.dumps(list(daily.values()))
        balance_dates_list = list(daily.keys())
    else:
        balance_dates_list = []

    return render(request, "dashboard/home.html", {
        "accounts": accounts,
        "account_stats": account_stats,
        "spend_pct": spend_pct,
        "category_labels": category_labels,
        "category_data": category_data,
        "category_data_zipped": category_data_zipped,
        "balance_dates": balance_dates,
        "balance_dates_list": balance_dates_list,
        "balance_values": balance_values,
    })



@login_required
def analytics_view(request):
    """
    Analytics page: spend-by-category pie chart + balance-over-time line chart.

    All chart data is passed to the template as JSON strings so the template
    can hand them straight to Chart.js without any extra AJAX call.
    """
    customer = getattr(request.user, "customer", None)
    if customer is None:
        return redirect("dashboard:home")
    if not customer.is_approved():
        return redirect("dashboard:home")

    account = customer.accounts.first()
    if account is None:
        # No account yet — render with empty data.
        return render(request, "dashboard/analytics.html", {
            "category_labels": json.dumps([]),
            "category_data": json.dumps([]),
            "balance_dates": json.dumps([]),
            "balance_values": json.dumps([]),
        })

    # ------------------------------------------------------------------ #
    # 1. Spend by category (pie chart)
    #    Debit entries on this account, grouped by tx category, summed.
    # ------------------------------------------------------------------ #
    debit_entries = (
        LedgerEntry.objects
        .filter(account=account, entry_type=LedgerEntry.EntryType.DEBIT)
        .select_related("transaction")
    )

    category_totals: dict[str, Decimal] = defaultdict(Decimal)
    for entry in debit_entries:
        cat = entry.transaction.category or "Other"
        category_totals[cat] += entry.amount

    category_labels = list(category_totals.keys())
    category_data = [float(v) for v in category_totals.values()]

    # ------------------------------------------------------------------ #
    # 2. Balance over time (line chart)
    #    Walk all ledger entries for this account in chronological order,
    #    grouping by date, and record the balance_after of the last entry
    #    each day.
    # ------------------------------------------------------------------ #
    all_entries = (
        LedgerEntry.objects
        .filter(account=account)
        .order_by("created_at")
        .values("created_at", "balance_after")
    )

    daily_balance: dict[str, float] = {}
    for entry in all_entries:
        # Convert to local date string (YYYY-MM-DD) so we group by calendar day.
        dt = entry["created_at"]
        if timezone.is_aware(dt):
            dt = timezone.localtime(dt)
        day_str = dt.strftime("%Y-%m-%d")
        daily_balance[day_str] = float(entry["balance_after"])

    balance_dates = list(daily_balance.keys())
    balance_values = list(daily_balance.values())

    return render(request, "dashboard/analytics.html", {
        "category_labels": json.dumps(category_labels),
        "category_data": json.dumps(category_data),
        "balance_dates": json.dumps(balance_dates),
        "balance_values": json.dumps(balance_values),
    })

