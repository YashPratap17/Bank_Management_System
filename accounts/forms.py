# from django import forms
# from django.contrib.auth.models import User
# from django.contrib.auth.password_validation import validate_password

# from .models import Customer, validate_roll_number


# class StudentRegistrationForm(forms.Form):
#     full_name = forms.CharField(max_length=150, label="Full name")
#     roll_number = forms.CharField(
#         max_length=20, label="Roll number",
#         validators=[validate_roll_number],
#         help_text="This will also be your account number.",
#     )
#     branch = forms.CharField(max_length=50, required=True, label="Branch (e.g. CSE)")
#     password = forms.CharField(widget=forms.PasswordInput, label="Password")
#     confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

#     def clean_roll_number(self):
#         roll_number = self.cleaned_data["roll_number"].strip().upper()
#         if Customer.objects.filter(roll_number=roll_number).exists():
#             raise forms.ValidationError("An account with this roll number already exists.")
#         if User.objects.filter(username=roll_number).exists():
#             raise forms.ValidationError("An account with this roll number already exists.")
#         return roll_number

#     def clean_password(self):
#         password = self.cleaned_data["password"]
#         validate_password(password)
#         return password

#     def clean(self):
#         cleaned = super().clean()
#         if cleaned.get("password") and cleaned.get("confirm_password"):
#             if cleaned["password"] != cleaned["confirm_password"]:
#                 raise forms.ValidationError("Passwords do not match.")
#         return cleaned


import re
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator

from .models import Customer


# 13‑digit roll number that must start with one of the allowed prefixes
ROLL_NUMBER_PATTERN = r'^(230122|240122|250122|260122)\d{7}$'
roll_number_validator = RegexValidator(
    regex=ROLL_NUMBER_PATTERN,
    message="Roll number must be 13 digits and start with 230122, 240122, 250122, or 260122."
)


BRANCH_CHOICES = [
    ("", "Select your branch"),
    ("CSE", "CSE - Computer Science & Engineering"),
    ("AL",  "AL - Artificial Intelligence & Machine Learning"),
    ("IoT", "IoT - Internet of Things"),
    ("CY",  "CY - Cyber Security"),
    ("DS",  "DS - Data Science"),
    ("IT",  "IT - Information Technology"),
]


class StudentRegistrationForm(forms.Form):
    full_name = forms.CharField(
        max_length=150,
        label="Full name"
    )
    roll_number = forms.CharField(
        max_length=13,
        min_length=13,
        label="University Roll Number",
        validators=[roll_number_validator],
        help_text="Must be your 13‑digit university roll number (e.g., 2401221234567).",
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. 2401221234567',
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]{13}',   # HTML5 validation
            'title': '13‑digit number starting with 230122, 240122, 250122, or 260122',
        })
    )
    branch = forms.ChoiceField(
        choices=BRANCH_CHOICES,
        label="Branch / Programme",
        required=True,
        error_messages={'required': 'Please select your branch.'},
        widget=forms.Select(attrs={'class': 'input-field'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm password"
    )

    def clean_roll_number(self):
        roll_number = self.cleaned_data["roll_number"].strip()
        # The regex already ensures length and pattern, but we still
        # check uniqueness.
        if Customer.objects.filter(roll_number=roll_number).exists():
            raise forms.ValidationError("An account with this roll number already exists.")
        if User.objects.filter(username=roll_number).exists():
            raise forms.ValidationError("An account with this roll number already exists.")
        return roll_number

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm = cleaned.get("confirm_password")
        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned