from django.urls import path
from . import views

# No app_name – so URL names are global (matches the template's {% url 'api_face_login' %})

urlpatterns = [
    # Face registration page (webcam)
    path('register-face/', views.register_face, name='register_face'),

    # API endpoints for face data
    path('api/register-face/', views.api_register_face, name='api_register_face'),
    path('api/face-login/', views.api_face_login, name='api_face_login'),
]