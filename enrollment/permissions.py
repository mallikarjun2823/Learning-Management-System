from rest_framework.permissions import BasePermission


class IsInstructor(BasePermission):
	"""Allow access only to authenticated users with instructor role."""

	def has_permission(self, request, view) -> bool:  # type: ignore[override]
		user = request.user
		user_role_num = getattr(getattr(user, "role", None), "role_num", None)
		return bool(getattr(user, "is_authenticated", False) and user_role_num == "INST")

