from decimal import Decimal, InvalidOperation
from django import forms

from accounts.models import Account


class AmountForm(forms.Form):
    """Base for deposit/withdraw: just an amount and an optional note."""
    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    description = forms.CharField(max_length=255, required=False)


class TransferForm(forms.Form):
    recipient_roll_number = forms.CharField(
        max_length=20, label="Recipient's roll number / account number"
    )
    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    description = forms.CharField(max_length=255, required=False)
    
    CATEGORY_CHOICES = [
        ("AUTO", "Auto-categorize"),
        ("Food", "Food"),
        ("Transport", "Transport"),
        ("Shopping", "Shopping"),
        ("Entertainment", "Entertainment"),
        ("Bills", "Bills"),
        ("Education", "Education"),
        ("Other", "Other"),
    ]
    category = forms.ChoiceField(choices=CATEGORY_CHOICES, required=False, initial="AUTO")

    def __init__(self, *args, sender_account=None, **kwargs):
        self.sender_account = sender_account
        super().__init__(*args, **kwargs)

    def clean_recipient_roll_number(self):
        roll_number = self.cleaned_data["recipient_roll_number"].strip().upper()
        try:
            recipient_account = Account.objects.select_related("customer").get(account_number=roll_number)
        except Account.DoesNotExist:
            raise forms.ValidationError("No account found with that roll number.")

        if self.sender_account and recipient_account.pk == self.sender_account.pk:
            raise forms.ValidationError("You can't transfer money to your own account.")

        self.cleaned_data["recipient_account"] = recipient_account
        return roll_number
