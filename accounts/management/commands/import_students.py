"""
Bulk-create student accounts from a CSV for the live demo.

CSV format (header row required):
    roll_number,full_name,branch,password
    2203031130123,Rohan Gupta,CSE,changeme123
    2203031130124,Priya Singh,CSE,changeme123

If the `password` column is omitted, each student's roll number is used as
their initial password (tell them to change it — or just leave it, this is
a training demo, not a production bank).

Usage:
    python manage.py import_students path/to/classmates.csv
    python manage.py import_students path/to/classmates.csv --dry-run
"""
import csv

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction

from accounts.models import Customer, Account


class Command(BaseCommand):
    help = "Bulk import classmate accounts from a CSV file. Imported accounts are auto-approved."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument("--dry-run", action="store_true", help="Validate without writing to the database.")

    def handle(self, *args, **options):
        path = options["csv_path"]
        dry_run = options["dry_run"]

        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            raise CommandError(f"File not found: {path}")

        if not rows:
            self.stdout.write(self.style.WARNING("CSV is empty — nothing to import."))
            return

        required_cols = {"roll_number", "full_name"}
        missing = required_cols - set(rows[0].keys())
        if missing:
            raise CommandError(f"CSV is missing required column(s): {missing}")

        created, skipped = 0, 0

        for row in rows:
            roll_number = row["roll_number"].strip().upper()
            full_name = row["full_name"].strip()
            branch = row.get("branch", "").strip()
            password = row.get("password", "").strip() or roll_number

            if not roll_number or not full_name:
                self.stdout.write(self.style.WARNING(f"Skipping incomplete row: {row}"))
                skipped += 1
                continue

            if User.objects.filter(username=roll_number).exists() or Customer.objects.filter(roll_number=roll_number).exists():
                self.stdout.write(f"  already exists, skipping: {roll_number} ({full_name})")
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f"  would create: {roll_number} — {full_name} ({branch})")
                created += 1
                continue

            with db_transaction.atomic():
                user = User.objects.create_user(username=roll_number, password=password,
                                                  first_name=full_name.split(" ")[0])
                customer = Customer.objects.create(
                    user=user, full_name=full_name, roll_number=roll_number, branch=branch,
                    approval_status=Customer.ApprovalStatus.APPROVED,
                )
                Account.objects.create(customer=customer, account_type=Account.AccountType.SAVINGS)

            self.stdout.write(self.style.SUCCESS(f"  created: {roll_number} — {full_name} ({branch})"))
            created += 1

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"\n{prefix}Done. Created: {created}, skipped (duplicates/incomplete): {skipped}."
        ))
