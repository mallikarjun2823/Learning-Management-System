from django.utils import timezone

from courses.models import Course, User

from .models import Enrollment


class EnrollmentError(ValueError):
	"""Base class for enrollment-related domain errors."""


class EnrollmentNotFound(EnrollmentError):
	"""Raised when an enrollment or related object cannot be found."""


class EnrollmentPermissionError(EnrollmentError):
	"""Raised when the user is not allowed to perform an operation."""


class EnrollmentValidationError(EnrollmentError):
	"""Raised when a request violates enrollment invariants or state rules."""


class EnrollmentService:
	"""Domain service for enrollment operations.

	Views should call into this service and handle HTTP concerns
	(status codes, response formatting), keeping business rules here.
	"""

	def _user_role_num(self, user: User) -> str | None:
		return getattr(getattr(user, "role", None), "role_num", None)

	def get_instructor_overview(self, instructor: User):
		"""Return courses taught by instructor with grouped enrollments.

		Result shape:
		[
			{
				"course": <Course>,
				"enrollments": {
					"invited": [<Enrollment>, ...],
					"active": [...],
					"closed": [...],
				},
			},
			...
		]
		"""

		courses = (
			Course.objects.filter(instructor=instructor)
			.prefetch_related("enrollments__user")
		)
		result: list[dict] = []
		for course in courses:
			invited: list[Enrollment] = []
			active: list[Enrollment] = []
			closed: list[Enrollment] = []
			for enr in course.enrollments.all():
				if enr.status == Enrollment.Status.INVITED:
					invited.append(enr)
				elif enr.status == Enrollment.Status.ACTIVE:
					active.append(enr)
				else:
					closed.append(enr)
			result.append(
				{
					"course": course,
					"enrollments": {
						"invited": invited,
						"active": active,
						"closed": closed,
					},
				}
			)
		return result

	def get_student_overview(self, student: User):
		"""Return the student's enrollments grouped by status.

		Result shape:
		{"invited": [...], "active": [...], "closed": [...]} with
		lists of Enrollment instances.
		"""

		qs = Enrollment.objects.filter(user=student).select_related("course")
		invited: list[Enrollment] = []
		active: list[Enrollment] = []
		closed: list[Enrollment] = []
		for enr in qs:
			if enr.status == Enrollment.Status.INVITED:
				invited.append(enr)
			elif enr.status == Enrollment.Status.ACTIVE:
				active.append(enr)
			else:
				closed.append(enr)
		return {"invited": invited, "active": active, "closed": closed}

	def invite_student_to_course(self, instructor: User, course_id: int, student_id: int) -> Enrollment:
		"""Invite a student to a course.

		Invariants:
		- Instructor must own the course.
		- Student must exist.
		- No existing ACTIVE or INVITED enrollment for this (student, course).
		"""

		try:
			course = Course.objects.get(id=course_id)
		except Course.DoesNotExist:
			raise EnrollmentNotFound("Course not found.")

		if course.instructor_id != instructor.id:
			raise EnrollmentPermissionError("You are not the instructor for this course.")

		try:
			student = User.objects.get(id=student_id)
		except User.DoesNotExist:
			raise EnrollmentValidationError("Student not found.")

		existing = (
			Enrollment.objects.filter(user=student, course=course)
			.order_by("-id")
			.first()
		)
		if existing and existing.status in (Enrollment.Status.ACTIVE, Enrollment.Status.INVITED):
			if existing.status == Enrollment.Status.ACTIVE:
				msg = "Student is already enrolled in this course."
			else:
				msg = "An invitation has already been sent to this student for this course."
			raise EnrollmentValidationError(msg)

		return Enrollment.objects.create(
			user=student,
			course=course,
			status=Enrollment.Status.INVITED,
			invited_at=timezone.now(),
		)

	def get_enrollment_for_user(self, user: User, enrollment_id: int) -> Enrollment:
		"""Return an enrollment if the user is allowed to see it."""

		try:
			enrollment = Enrollment.objects.select_related("course", "user").get(id=enrollment_id)
		except Enrollment.DoesNotExist:
			raise EnrollmentNotFound("Enrollment not found.")

		user_role_num = self._user_role_num(user)
		if user_role_num == "INST" and enrollment.course.instructor_id == user.id:
			return enrollment
		if enrollment.user_id == user.id:
			return enrollment
		raise EnrollmentPermissionError("You do not have access to this enrollment.")

	def accept_enrollment(self, user: User, enrollment_id: int) -> Enrollment:
		"""Accept an invited enrollment as the owning student."""

		user_role_num = self._user_role_num(user)
		if user_role_num != "STUD":
			raise EnrollmentValidationError("No supported action for this role.")

		enrollment = self.get_enrollment_for_user(user, enrollment_id)
		if enrollment.user_id != user.id:
			raise EnrollmentPermissionError("You can only act on your own enrollments.")
		if enrollment.status != Enrollment.Status.INVITED:
			raise EnrollmentValidationError("Only invited enrollments can be accepted.")

		enrollment.status = Enrollment.Status.ACTIVE
		enrollment.activated_at = timezone.now()
		enrollment.save(update_fields=["status", "activated_at", "updated_at"])
		return enrollment

