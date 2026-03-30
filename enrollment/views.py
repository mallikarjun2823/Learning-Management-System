from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from courses.models import Course, User
from courses.serializers import CourseSerializer

from .models import Enrollment
from .serializers import (
	EnrollmentSerializer,
	EnrollmentInviteSerializer,
	EnrollmentActionSerializer,
)
from .permissions import IsInstructor
from .services import (
	EnrollmentService,
	EnrollmentNotFound,
	EnrollmentPermissionError,
	EnrollmentValidationError,
)


class EnrollmentListView(APIView):

	permission_classes = [IsAuthenticated]

	def get(self, request):
		user = request.user
		service = EnrollmentService()
		user_role_num = getattr(getattr(user, "role", None), "role_num", None)

		if user_role_num == "INST":
			overview = service.get_instructor_overview(user)
			payload = []
			for item in overview:
				course = item["course"]
				groups = item["enrollments"]
				payload.append(
					{
						"course": CourseSerializer(course).data,
						"enrollments": {
							"invited": EnrollmentSerializer(groups["invited"], many=True).data,
							"active": EnrollmentSerializer(groups["active"], many=True).data,
							"closed": EnrollmentSerializer(groups["closed"], many=True).data,
						},
					}
				)
			return Response(payload)

		groups = service.get_student_overview(user)
		return Response(
			{
				"invited": EnrollmentSerializer(groups["invited"], many=True).data,
				"active": EnrollmentSerializer(groups["active"], many=True).data,
				"closed": EnrollmentSerializer(groups["closed"], many=True).data,
			}
		)


class EnrollmentDetailView(APIView):

	permission_classes = [IsAuthenticated]

	def get(self, request, enrollment_id: int):
		service = EnrollmentService()
		try:
			enrollment = service.get_enrollment_for_user(request.user, enrollment_id)
		except EnrollmentNotFound as e:
			return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
		except EnrollmentPermissionError as e:
			return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
		return Response(EnrollmentSerializer(enrollment).data)

	def post(self, request, enrollment_id: int):
		"""Perform an action on a single enrollment.

		Currently supports:
		- Students: {"action": "accept"} to accept an INVITED enrollment.
		"""

		action_serializer = EnrollmentActionSerializer(data=request.data)
		action_serializer.is_valid(raise_exception=True)

		service = EnrollmentService()
		try:
			enrollment = service.accept_enrollment(request.user, enrollment_id)
		except EnrollmentNotFound as e:
			return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
		except EnrollmentPermissionError as e:
			return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
		except EnrollmentValidationError as e:
			return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
		return Response(EnrollmentSerializer(enrollment).data)


class EnrollmentInviteView(APIView):
	"""Invite a single student to enroll in a course.

	Rules:
	- Request user must be an instructor.
	- They must be the instructor for the target course.
	- Target student must not already have an ACTIVE or INVITED enrollment
	  for this course.
	"""

	permission_classes = [IsAuthenticated, IsInstructor]

	def post(self, request, course_id: int):
		serializer = EnrollmentInviteSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		student_id = serializer.validated_data["student_id"]

		service = EnrollmentService()
		try:
			enrollment = service.invite_student_to_course(request.user, course_id, student_id)
		except EnrollmentNotFound as e:
			return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
		except EnrollmentPermissionError as e:
			return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
		except EnrollmentValidationError as e:
			return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

		return Response(
			EnrollmentSerializer(enrollment).data,
			status=status.HTTP_201_CREATED,
		)

