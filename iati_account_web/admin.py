from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import IATIUser

admin.site.register(IATIUser, UserAdmin)
