from django.db import models
from courses.models import Course
from courses.models import User

from django.conf import settings
from django.db import models

class Enrollment(models.Model):
    
# Create your models here.
	"""Enrollment of a user in a course.

	Links the custom User model (courses.User via AUTH_USER_MODEL)
	to a Course, and tracks the high-level enrollment status and
	key lifecycle timestamps.
	"""

	class Status(models.TextChoices):
		INVITED = "INVITED", "Invited"
		ACTIVE = "ACTIVE", "Active"
		COMPLETED = "COMPLETED", "Completed"
		WITHDRAWN = "WITHDRAWN", "Withdrawn"
		SUSPENDED = "SUSPENDED", "Suspended"

	user = models.ForeignKey(
		User,
		on_delete=models.PROTECT,
		related_name="enrollments",
	)
	course = models.ForeignKey(
		Course,
		on_delete=models.PROTECT,
		related_name="enrollments",
	)
	status = models.CharField(
		max_length=20,
		choices=Status.choices,
		default=Status.INVITED,
	)

	invited_at = models.DateTimeField(null=True, blank=True)
	activated_at = models.DateTimeField(null=True, blank=True)
	completed_at = models.DateTimeField(null=True, blank=True)
	suspended_at = models.DateTimeField(null=True, blank=True)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		indexes = [
			models.Index(fields=["course", "status"]),
			models.Index(fields=["user", "status"]),
		]

	def __str__(self) -> str:
		return f"Enrollment(user={self.user_id}, course={self.course_id}, status={self.status})"
