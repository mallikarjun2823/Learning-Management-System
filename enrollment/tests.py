from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import User, Course, RoleLookup
from enrollment.models import Enrollment


class EnrollmentAPITests(APITestCase):
	def setUp(self):
		instructor_role, _ = RoleLookup.objects.get_or_create(
			role_num="INST", defaults={"role_name": "INSTRUCTOR"}
		)
		student_role, _ = RoleLookup.objects.get_or_create(
			role_num="STUD", defaults={"role_name": "STUDENT"}
		)

		self.instructor = User.objects.create_user(
			username="instructor1",
			email="instr@example.com",
			password="password",
			role=instructor_role,
		)
		self.student = User.objects.create_user(
			username="student1",
			email="stud@example.com",
			password="password",
			role=student_role,
		)

		self.course = Course.objects.create(
			title="Test Course",
			description="Desc",
			instructor=self.instructor,
		)

	def test_instructor_get_enrollments_lists_courses_and_enrollments(self):
		# Create a few enrollments with different statuses
		Enrollment.objects.create(
			user=self.student,
			course=self.course,
			status=Enrollment.Status.INVITED,
			invited_at=timezone.now(),
		)

		self.client.force_authenticate(user=self.instructor)
		url = reverse("enrollment-list")
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertEqual(len(resp.data), 1)
		item = resp.data[0]
		self.assertIn("course", item)
		self.assertIn("enrollments", item)
		self.assertTrue(item["enrollments"]["invited"])  # has at least one invited

	def test_student_get_enrollments_grouped_by_status(self):
		Enrollment.objects.create(
			user=self.student,
			course=self.course,
			status=Enrollment.Status.INVITED,
			invited_at=timezone.now(),
		)

		self.client.force_authenticate(user=self.student)
		url = reverse("enrollment-list")
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertIn("invited", resp.data)
		self.assertGreaterEqual(len(resp.data["invited"]), 1)

	def test_only_instructor_can_invite_student(self):
		url = reverse("course-invite-student", kwargs={"course_id": self.course.id})

		# Student should not be allowed
		self.client.force_authenticate(user=self.student)
		resp_student = self.client.post(url, {"student_id": self.student.id}, format="json")
		self.assertIn(resp_student.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST))

		# Instructor can invite
		self.client.force_authenticate(user=self.instructor)
		resp_instr = self.client.post(url, {"student_id": self.student.id}, format="json")
		self.assertEqual(resp_instr.status_code, status.HTTP_201_CREATED)
		self.assertEqual(resp_instr.data["status"], Enrollment.Status.INVITED)

	def test_invite_fails_with_unknown_student(self):
		"""Inviting a non-existent student should return 400 from serializer validation."""
		self.client.force_authenticate(user=self.instructor)
		url = reverse("course-invite-student", kwargs={"course_id": self.course.id})
		# Use an ID that does not exist in the test DB
		resp = self.client.post(url, {"student_id": 99999}, format="json")
		self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

	def test_instructor_cannot_invite_for_course_they_do_not_own(self):
		other_instr = User.objects.create_user(
			username="otherinstr",
			email="otherinstr@example.com",
			password="password",
			role=self.instructor.role,
		)
		other_course = Course.objects.create(
			title="Other Course",
			description="Desc",
			instructor=other_instr,
		)
		self.client.force_authenticate(user=self.instructor)
		url = reverse("course-invite-student", kwargs={"course_id": other_course.id})
		resp = self.client.post(url, {"student_id": self.student.id}, format="json")
		self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

	def test_invite_rejected_if_already_active_or_invited(self):
		url = reverse("course-invite-student", kwargs={"course_id": self.course.id})
		self.client.force_authenticate(user=self.instructor)

		# First invite succeeds
		resp1 = self.client.post(url, {"student_id": self.student.id}, format="json")
		self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)

		# Second invite should fail because already INVITED
		resp2 = self.client.post(url, {"student_id": self.student.id}, format="json")
		self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)

		# Mark as ACTIVE then try again
		enr = Enrollment.objects.get(user=self.student, course=self.course)
		enr.status = Enrollment.Status.ACTIVE
		enr.save(update_fields=["status"])
		resp3 = self.client.post(url, {"student_id": self.student.id}, format="json")
		self.assertEqual(resp3.status_code, status.HTTP_400_BAD_REQUEST)

	def test_student_can_accept_own_invited_enrollment(self):
		enrollment = Enrollment.objects.create(
			user=self.student,
			course=self.course,
			status=Enrollment.Status.INVITED,
			invited_at=timezone.now(),
		)
		url = reverse("enrollment-detail", kwargs={"enrollment_id": enrollment.id})

		self.client.force_authenticate(user=self.student)
		resp = self.client.post(url, {"action": "accept"}, format="json")
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		enrollment.refresh_from_db()
		self.assertEqual(enrollment.status, Enrollment.Status.ACTIVE)

	def test_student_cannot_accept_non_invited_or_someone_elses_enrollment(self):
		other_student = User.objects.create_user(
			username="student2",
			email="stud2@example.com",
			password="password",
			role=self.student.role,
		)
		enrollment = Enrollment.objects.create(
			user=other_student,
			course=self.course,
			status=Enrollment.Status.ACTIVE,
		)
		url = reverse("enrollment-detail", kwargs={"enrollment_id": enrollment.id})

		self.client.force_authenticate(user=self.student)
		resp = self.client.post(url, {"action": "accept"}, format="json")
		# Not allowed: wrong user and wrong status
		self.assertIn(resp.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST))

	def test_student_double_accept_fails_second_time(self):
		enrollment = Enrollment.objects.create(
			user=self.student,
			course=self.course,
			status=Enrollment.Status.INVITED,
			invited_at=timezone.now(),
		)
		url = reverse("enrollment-detail", kwargs={"enrollment_id": enrollment.id})
		self.client.force_authenticate(user=self.student)
		# First accept succeeds
		resp1 = self.client.post(url, {"action": "accept"}, format="json")
		self.assertEqual(resp1.status_code, status.HTTP_200_OK)
		# Second accept should fail because status is now ACTIVE
		resp2 = self.client.post(url, {"action": "accept"}, format="json")
		self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)

	def test_instructor_cannot_accept_enrollment(self):
		enrollment = Enrollment.objects.create(
			user=self.student,
			course=self.course,
			status=Enrollment.Status.INVITED,
		)
		url = reverse("enrollment-detail", kwargs={"enrollment_id": enrollment.id})
		self.client.force_authenticate(user=self.instructor)
		resp = self.client.post(url, {"action": "accept"}, format="json")
		self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

	def test_instructor_or_student_can_view_permitted_enrollment_detail(self):
		enrollment = Enrollment.objects.create(
			user=self.student,
			course=self.course,
			status=Enrollment.Status.INVITED,
		)
		url = reverse("enrollment-detail", kwargs={"enrollment_id": enrollment.id})

		# Instructor view
		self.client.force_authenticate(user=self.instructor)
		resp_instr = self.client.get(url)
		self.assertEqual(resp_instr.status_code, status.HTTP_200_OK)

		# Student view
		self.client.force_authenticate(user=self.student)
		resp_stud = self.client.get(url)
		self.assertEqual(resp_stud.status_code, status.HTTP_200_OK)

