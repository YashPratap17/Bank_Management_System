from django.urls import path
from . import views

app_name = "ai_insights"

urlpatterns = [
    path("risk/", views.risk_dashboard, name="risk_dashboard"),
    path("approvals/", views.approvals_dashboard, name="approvals_dashboard"),
    path("approvals/<int:customer_id>/approve/", views.approve_customer, name="approve_customer"),
    path("approvals/<int:customer_id>/reject/", views.reject_customer, name="reject_customer"),
]
