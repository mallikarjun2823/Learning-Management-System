from rest_framework.permissions import BasePermission


class CoursePermission(BasePermission):
    """Permission check: only instructors can create courses."""
    def has_permission(self, request, view):
        user = request.user
        user_role_num = getattr(getattr(user, 'role', None), 'role_num', None)
        if getattr(user, 'is_authenticated', False) and user_role_num == 'INST':
            return True
        return False
class CourseDetailPermission(BasePermission):
    """Permission check: only instructors can edit/delete course details."""
    def has_object_permission(self, request, view, obj):
        user = request.user
        course_instructor = getattr(obj, 'instructor', None)
        user_role_num = getattr(getattr(user, 'role', None), 'role_num', None)
        if getattr(user, 'is_authenticated', False) and user_role_num == 'INST' and course_instructor == user.id:
            return True
        return False