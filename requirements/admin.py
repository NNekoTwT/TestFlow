from django.contrib import admin

from .models import Requirement


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "module", "created_at")
    search_fields = ("title", "module", "description")
    list_filter = ("module",)
