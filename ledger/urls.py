from django.urls import path
from . import views

app_name = "ledger"

urlpatterns = [
    path("deposit/", views.deposit_view, name="deposit"),
    path("withdraw/", views.withdraw_view, name="withdraw"),
    path("transfer/", views.transfer_view, name="transfer"),
    path("history/", views.history_view, name="history"),
    path("history/download/", views.download_statement_view, name="download_statement"),
    path("api/account-lookup/", views.account_lookup, name="account_lookup"),
]