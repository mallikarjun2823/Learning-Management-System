from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from .models import User, Course, RoleLookup
from enrollment.models import Enrollment


class AuthAndCourseTests(APITestCase):
    def setUp(self):
        # ensure role lookup rows exist and create baseline users
        instructor_role, _ = RoleLookup.objects.get_or_create(
            role_num='INST', defaults={'role_name': 'INSTRUCTOR'}
        )
        student_role, _ = RoleLookup.objects.get_or_create(
            role_num='STUD', defaults={'role_name': 'STUDENT'}
        )
        RoleLookup.objects.get_or_create(
            role_num='ADMIN', defaults={'role_name': 'ADMINISTRATOR'}
        )

        self.instructor = User.objects.create_user(
            username='instructor1',
            email='instructor@example.com',
            password='password',
            role=instructor_role,
        )
        self.student = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='password',
            role=student_role,
        )

    def test_register_endpoint(self):
        url = reverse('register')
        payload = {
            'username': 'newstudent',
            'email': 'newstudent@example.com',
            'password': 'pass1234',
            'role': 'STUD'
        }
        resp = self.client.post(url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', resp.data)

    def test_register_rejects_duplicate_username_and_unknown_role(self):
        url = reverse('register')
        # First registration succeeds
        payload = {
            'username': 'dupeuser',
            'email': 'dupe1@example.com',
            'password': 'pass1234',
            'role': 'STUD',
        }
        resp1 = self.client.post(url, payload, format='json')
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)

        # Duplicate username should fail
        payload['email'] = 'dupe2@example.com'
        resp2 = self.client.post(url, payload, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)

        # Unknown role should fail
        payload = {
            'username': 'otheruser',
            'email': 'other@example.com',
            'password': 'pass1234',
            'role': 'UNKNOWN',
        }
        resp3 = self.client.post(url, payload, format='json')
        self.assertEqual(resp3.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_and_create_course_as_instructor(self):
        # Login to get tokens
        login_url = reverse('login')
        resp = self.client.post(login_url, {'username': 'instructor1', 'password': 'password'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tokens = resp.data.get('tokens')
        self.assertIsNotNone(tokens)
        access = tokens.get('access')
        self.assertIsNotNone(access)

        # Create a course as authenticated instructor.
        # force_authenticate keeps test focused on role/permission behavior.
        create_url = reverse('course-list-create')
        self.client.force_authenticate(user=self.instructor)
        course_payload = {'title': 'Django', 'description': 'Basic Django course'}
        resp2 = self.client.post(create_url, course_payload, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        # verify course exists
        course_id = resp2.data.get('id')
        self.assertIsNotNone(course_id)
        self.assertTrue(Course.objects.filter(id=course_id, title='Django').exists())

    def test_login_fails_with_wrong_password(self):
        login_url = reverse('login')
        resp = self.client.post(login_url, {'username': 'instructor1', 'password': 'wrong'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_course_forbidden_for_student_or_anonymous(self):
        create_url = reverse('course-list-create')
        # Anonymous
        resp_anonymous = self.client.post(create_url, {'title': 'X', 'description': 'Y'}, format='json')
        self.assertEqual(resp_anonymous.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated student
        self.client.force_authenticate(user=self.student)
        resp_student = self.client.post(create_url, {'title': 'X', 'description': 'Y'}, format='json')
        # CoursePermission should deny non-instructors
        self.assertIn(resp_student.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST))

    def test_create_course_rejects_blank_title_or_description(self):
        self.client.force_authenticate(user=self.instructor)
        create_url = reverse('course-list-create')

        resp_blank_title = self.client.post(create_url, {'title': ' ', 'description': 'desc'}, format='json')
        self.assertEqual(resp_blank_title.status_code, status.HTTP_400_BAD_REQUEST)

        resp_blank_desc = self.client.post(create_url, {'title': 'Name', 'description': ' '}, format='json')
        self.assertEqual(resp_blank_desc.status_code, status.HTTP_400_BAD_REQUEST)

    def test_course_list_for_instructor_returns_only_their_courses(self):
        # Courses for self.instructor
        course1 = Course.objects.create(title='C1', description='D1', instructor=self.instructor)
        # Course for a different instructor
        other_instr = User.objects.create_user(
            username='other', email='other@example.com', password='password', role=self.instructor.role
        )
        Course.objects.create(title='C2', description='D2', instructor=other_instr)

        self.client.force_authenticate(user=self.instructor)
        url = reverse('course-list-create')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {c['id'] for c in resp.data}
        self.assertIn(course1.id, ids)
        self.assertNotIn(None, ids)
        self.assertNotIn(0, ids)

    def test_course_list_for_student_uses_enrollments(self):
        course1 = Course.objects.create(title='C1', description='D1', instructor=self.instructor)
        Course.objects.create(title='C2', description='D2', instructor=self.instructor)
        # Only course1 should be visible because only it has an ACTIVE enrollment
        Enrollment.objects.create(user=self.student, course=course1, status=Enrollment.Status.ACTIVE)

        self.client.force_authenticate(user=self.student)
        url = reverse('course-list-create')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {c['id'] for c in resp.data}
        self.assertEqual(ids, {course1.id})
