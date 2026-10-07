from django.contrib import admin

from .models import GenerationRecord, TestCase, TestPoint


@admin.register(TestPoint)
class TestPointAdmin(admin.ModelAdmin):
    list_display = ("id", "requirement", "title", "category", "priority", "selected", "design_method")
    list_filter = ("category", "priority", "design_method")
    list_editable = ("selected",)


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ("id", "case_id", "requirement", "title", "test_type", "priority", "design_method")
    list_filter = ("test_type", "priority", "design_method")
    search_fields = ("case_id", "title")


@admin.register(GenerationRecord)
class GenerationRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "requirement", "status", "model", "duration_ms", "created_at")
    list_filter = ("status", "model")
