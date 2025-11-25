from django.urls import path

from . import views

app_name = "account"

urlpatterns = [
    path("", views.self_service, name="home"),
    path("onboarding", views.onboarding, name="start-onboarding"),
]
