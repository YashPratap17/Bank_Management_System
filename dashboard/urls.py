from django.urls import path
from . import views
from accounts import views as account_views
app_name = "dashboard"

urlpatterns = [
    path("", views.landing_or_dashboard, name="home"),
    path("register/", views.register_view, name="register"),
    path("analytics/", views.analytics_view, name="analytics"),
    path("apply-credit-card/", views.apply_credit_card, name="apply_credit_card"),
    path("manage-cards/", views.manage_cards_view, name="manage_cards"),
    path("manage-cards/<int:card_id>/toggle-status/", views.toggle_card_status, name="toggle_card_status"),
    path('accounts/register-face/', account_views.register_face, name='register_face'),
    path('api/register-face/', account_views.api_register_face, name='api_register_face'),
    path('api/face-login/', account_views.api_face_login, name='api_face_login'),
]
