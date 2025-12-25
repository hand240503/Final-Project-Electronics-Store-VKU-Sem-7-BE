# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_with_gemini, name='chat_with_gemini'),
    path('health/', views.chat_health_check, name='chat_health_check'),
]