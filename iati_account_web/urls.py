"""
URL configuration for IATI Account Web App project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path

from .identity import logout, provision_account

urlpatterns = [
    path("admin/", admin.site.urls),
    path("identity/oidc/", include("mozilla_django_oidc.urls")),
    path("identity/logout", logout, name="logout"),
    path("identity/provisioning", provision_account, name="provisioning"),
]

urlpatterns += i18n_patterns(
    path("i18n/", include("django.conf.urls.i18n"), name="set_language"),
    path("", include("iati_account_web.welcome.urls")),
    path("account/", include("iati_account_web.account.urls")),
    path("data/", include("iati_account_web.data.urls")),
)
