from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CiatUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active", "demande_en_attente")
    list_filter = ("role", "is_active", "demande_en_attente")
    fieldsets = UserAdmin.fieldsets + (("CIAT", {"fields": ("role", "fonction", "demande_en_attente", "motif")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("CIAT", {"fields": ("role", "fonction")}),)
