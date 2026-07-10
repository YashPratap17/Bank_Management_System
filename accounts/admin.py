from django.contrib import admin
from .models import Customer, Account, Card


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


@admin.action(description="Approve selected credit cards")
def approve_credit_cards(modeladmin, request, queryset):
    updated = queryset.filter(status=Card.Status.PENDING_APPROVAL).update(status=Card.Status.ACTIVE)
    modeladmin.message_user(request, f"Successfully approved {updated} credit card(s).")

@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("card_number", "account", "card_type", "status", "created_at")
    list_filter = ("card_type", "status")
    search_fields = ("card_number", "account__customer__full_name")
    actions = [approve_credit_cards]
