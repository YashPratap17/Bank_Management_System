from django.urls import path
from . import views
from accounts import views as account_views
app_name = "dashboard"

urlpatterns = [
    path("", views.landing_or_dashboard, name="home"),
    path("register/", views.register_view, name="register"),
    path("analytics/", views.analytics_view, name="analytics"),
    path('accounts/register-face/', account_views.register_face, name='register_face'),
    path('api/register-face/', account_views.api_register_face, name='api_register_face'),
    path('api/face-login/', account_views.api_face_login, name='api_face_login'),
]

