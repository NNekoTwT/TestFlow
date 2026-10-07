from rest_framework import serializers

from .models import Requirement


class RequirementSerializer(serializers.ModelSerializer):
    test_case_count = serializers.SerializerMethodField()

    class Meta:
        model = Requirement
        fields = [
            "id",
            "title",
            "module",
            "description",
            "created_at",
            "updated_at",
            "test_case_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "test_case_count"]

    def get_test_case_count(self, obj):
        return obj.test_cases.count()
