from django.urls import path

from . import views

app_name = "account"

urlpatterns = [
    path("", views.self_service, name="home"),
    path("welcome", views.onboarding, name="onboarding"),
]
