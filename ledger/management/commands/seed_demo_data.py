"""
Generates realistic demo data so the AI features (fraud detection,
categorization) have something meaningful to work on. Run this BEFORE
starting Day 3 — don't leave it for later, you cannot demo AI on an
empty database.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --flush   # wipe existing demo data first
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Customer, Account
from ledger.models import Transaction, LedgerEntry
from ledger.services import deposit, withdraw, transfer

# (description, category) pairs used to generate realistic, categorizable
# transaction descriptions. Day 3's categorizer will map these to categories.
NORMAL_SPENDING = [
    ("Zomato order", "Food"),
    ("Swiggy order", "Food"),
    ("Big Bazaar groceries", "Food"),
    ("Electricity bill payment", "Utilities"),
    ("Airtel postpaid bill", "Utilities"),
    ("Amazon purchase", "Shopping"),
    ("Myntra order", "Shopping"),
    ("Uber ride", "Transport"),
    ("Ola ride", "Transport"),
    ("Movie tickets BookMyShow", "Entertainment"),
    ("Netflix subscription", "Entertainment"),
    ("House rent", "Housing"),
]

SALARY_DESCRIPTIONS = ["Monthly salary credit", "Freelance payment received"]


class Command(BaseCommand):
    help = "Seed the database with demo customers, accounts, and transaction history."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush", action="store_true",
            help="Delete existing demo users/accounts before seeding.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing existing demo data...")
            User.objects.filter(username__startswith="DEMO").delete()

        random.seed(42)  # reproducible demo data across runs

        demo_people = [
            ("DEMO2201", "Alice Sharma"),
            ("DEMO2202", "Bob Verma"),
            ("DEMO2203", "Carol Mehta"),
        ]

        accounts = []
        for roll_number, full_name in demo_people:
            user, created = User.objects.get_or_create(
                username=roll_number, defaults={"email": f"{roll_number.lower()}@example.com"}
            )
            if created:
                user.set_password("demopass123")
                user.save()

            customer, _ = Customer.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": full_name,
                    "roll_number": roll_number,
                    "branch": "CSE",
                    "approval_status": Customer.ApprovalStatus.APPROVED,
                },
            )
            account, created = Account.objects.get_or_create(
                customer=customer,
                account_type=Account.AccountType.SAVINGS,
            ) if not customer.accounts.exists() else (customer.accounts.first(), False)

            accounts.append(account)
            self.stdout.write(f"  {'created' if created else 'reused'} account for {full_name}: {account.account_number}")

        # --- Generate 60 days of history per account ---
        today = timezone.now()
        for account in accounts:
            # Opening balance via a salary-like deposit
            deposit(account, Decimal("25000.00"), "Opening balance")

            for day_offset in range(60, 0, -1):
                tx_date = today - timedelta(days=day_offset)

                # Monthly salary credit around day-of-month 1
                if tx_date.day == 1:
                    tx = deposit(account, Decimal(random.randint(20000, 35000)),
                                 random.choice(SALARY_DESCRIPTIONS))
                    self._backdate(tx, tx_date)

                # 1-3 normal spends per day, most days
                if random.random() < 0.6:
                    for _ in range(random.randint(1, 3)):
                        desc, _cat = random.choice(NORMAL_SPENDING)
                        amount = Decimal(random.randint(150, 3000))
                        try:
                            tx = withdraw(account, amount, desc)
                            self._backdate(tx, tx_date, business_hours=True)
                        except Exception:
                            pass  # skip if insufficient funds on this pass

            # --- Inject a few deliberate anomalies for fraud detection to catch ---
            anomaly_date = today - timedelta(days=random.randint(2, 10))
            anomaly_amount = Decimal(random.randint(40000, 80000))
            try:
                # Ensure funds exist first — a sudden top-up followed by a
                # large odd-hour withdrawal is itself a realistic fraud
                # pattern, so this isn't just a workaround, it's good demo data.
                topup = deposit(account, anomaly_amount + Decimal("5000"), "Bonus credit")
                self._backdate(topup, anomaly_date - timedelta(hours=2))

                tx = withdraw(account, anomaly_amount, "Large withdrawal - unusual amount")
                self._backdate(tx, anomaly_date.replace(hour=3))  # 3 AM, odd hour
                tx.status = Transaction.Status.FLAGGED
                tx.save()
                self.stdout.write(self.style.WARNING(
                    f"  Injected anomaly for {account.account_number}: large odd-hour withdrawal"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Could not inject anomaly: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nSeeded {len(accounts)} accounts with ~60 days of transaction history."
        ))
        self.stdout.write("Demo logins: DEMO2201 / DEMO2202 / DEMO2203, password: demopass123")

    @staticmethod
    def _backdate(tx: Transaction, when, business_hours=False):
        """
        Transaction.created_at is auto_now_add, so we backdate it directly
        via update() (bypasses save()/auto_now_add without touching the
        immutability guard on LedgerEntry, since we're only adjusting the
        timestamp, not the financial fields).
        """
        if business_hours:
            when = when.replace(hour=random.randint(9, 21), minute=random.randint(0, 59))
        Transaction.objects.filter(pk=tx.pk).update(created_at=when)
        LedgerEntry.objects.filter(transaction=tx).update(created_at=when)
