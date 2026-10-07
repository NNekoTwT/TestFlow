from rest_framework import serializers

from .models import GenerationRecord, TestCase, TestPoint


class TestPointSerializer(serializers.ModelSerializer):
    test_case_count = serializers.SerializerMethodField()

    class Meta:
        model = TestPoint
        fields = [
            "id",
            "title",
            "description",
            "category",
            "priority",
            "design_method",
            "selected",
            "test_case_count",
            "created_at",
        ]
        read_only_fields = ["id", "test_case_count", "created_at"]

    def get_test_case_count(self, obj):
        return obj.test_cases.count()


class TestCaseSerializer(serializers.ModelSerializer):
    test_point_id = serializers.IntegerField(read_only=True)
    test_point_title = serializers.CharField(source="test_point.title", read_only=True, default="")

    class Meta:
        model = TestCase
        fields = [
            "id",
            "case_id",
            "module",
            "title",
            "preconditions",
            "steps",
            "test_data",
            "expected_result",
            "test_type",
            "priority",
            "design_method",
            "test_point_id",
            "test_point_title",
        ]


class GenerationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenerationRecord
        fields = [
            "id",
            "status",
            "model",
            "error_message",
            "duration_ms",
            "review_result",
            "created_at",
        ]
