from django.urls import path

from .views import EnrollmentListView, EnrollmentDetailView, EnrollmentInviteView

urlpatterns = [
	# GET /api/enrollments/ - role-aware enrollment overview
	path("enrollments/", EnrollmentListView.as_view(), name="enrollment-list"),
	# GET/POST /api/enrollments/<id>/ - per-enrollment actions (e.g., student accept)
	path("enrollments/<int:enrollment_id>/", EnrollmentDetailView.as_view(), name="enrollment-detail"),
	# POST /api/courses/<course_id>/invite/ - invite a single student
	path("courses/<int:course_id>/invite/", EnrollmentInviteView.as_view(), name="course-invite-student"),
]
