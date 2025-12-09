from django.urls import path

from . import views

app_name = "data"

urlpatterns = [
    path("", views.home, name="home"),
    path("organisation/<uuid:oid>", views.organisation_detail, name="reporting-org-detail"),
    path("organisation/<uuid:oid>/delete", views.organisation_delete, name="delete-organisation"),
    path("join-reporting-org", views.join_reporting_org, name="join-reporting-org"),
    path("organisation", views.create_organisation, name="create-reporting-org"),
    path("organisation/<uuid:oid>/datasets", views.dataset_list, name="dataset-list"),
    path("organisation/<uuid:oid>/datasets/new", views.create_dataset, name="create-dataset"),
    path("organisation/<uuid:oid>/datasets/<uuid:dataset_id>", views.dataset_detail, name="dataset-detail"),
    path("organisation/<uuid:oid>/datasets/<uuid:dataset_id>/delete", views.dataset_delete, name="delete-dataset"),
]
