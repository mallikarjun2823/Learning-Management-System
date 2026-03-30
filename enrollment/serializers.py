from rest_framework import serializers

from .models import Enrollment
from courses.models import User


class EnrollmentSerializer(serializers.ModelSerializer):
	class Meta:
		model = Enrollment
		fields = [
			"id",
			"user",
			"course",
			"status",
			"invited_at",
			"activated_at",
			"completed_at",
			"suspended_at",
			"created_at",
			"updated_at",
		]
		read_only_fields = fields


class EnrollmentInviteSerializer(serializers.Serializer):
	"""Payload for inviting a single student to a course."""

	student_id = serializers.IntegerField()

	def validate_student_id(self, value: int) -> int:
		if not User.objects.filter(id=value).exists():
			raise serializers.ValidationError("Student not found.")
		return value


class EnrollmentActionSerializer(serializers.Serializer):
	"""Payload for performing an action on an enrollment (e.g., accept)."""

	action = serializers.ChoiceField(choices=["accept"])

