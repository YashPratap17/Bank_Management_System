from django.contrib import admin
from .models import Transaction, LedgerEntry


class LedgerEntryInline(admin.TabularInline):
    model = LedgerEntry
    extra = 0
    readonly_fields = ("account", "entry_type", "amount", "balance_after", "created_at")
    can_delete = False


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("reference_id", "tx_type", "status", "category", "ai_risk_score", "created_at")
    list_filter = ("tx_type", "status", "category")
    inlines = [LedgerEntryInline]


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("account", "entry_type", "amount", "balance_after", "created_at")
    list_filter = ("entry_type",)
