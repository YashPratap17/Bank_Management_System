from django.contrib import admin
from .models import Customer, Account


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "roll_number", "branch", "approval_status", "created_at")
    list_filter = ("approval_status", "branch")
    search_fields = ("full_name", "roll_number", "user__username")


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("account_number", "customer", "account_type", "status", "opened_at")
    list_filter = ("account_type", "status")
    search_fields = ("account_number", "customer__full_name")
