"""Models for the courses app.

This module contains a simple learning-management hierarchy:

- `User` extends Django's `AbstractUser` with a `role` field.
- `Course` represents a course created by an instructor.
- `Module` groups lessons inside a `Course` and is ordered by `module_number`.
- `Lesson` belongs to a `Module` and is ordered by `lesson_number`.

Conventions:
- Use `related_name` on ForeignKey fields to provide a clear reverse relation
  (e.g. `user.instructed_courses`, `course.modules`, `module.lessons`).
"""

from django.db import models
from django.contrib.auth.models import AbstractUser

class RoleLookup(models.Model):
    """A lookup table for valid user roles.

    Stores role definitions with string role_num keys for easy validation and lookup.
    
    Fields:
    - `role_num` (str): unique role key (e.g., 'INST', 'STUD', 'ADMIN'). Use this
      in API payloads and role checks.
    - `role_name` (str): human-readable role name (e.g., 'INSTRUCTOR').
    
    Example:
        role = RoleLookup.objects.get(role_num='INST')
    """

    role_num = models.CharField(max_length=20, unique=True)
    role_name = models.CharField(max_length=50)

    class Meta:
        ordering = ['role_num']

    def __str__(self):
        return f"{self.role_num} ({self.role_name})"

class User(AbstractUser):
    """Application user with a role field.

    Fields:
    - `role` (str): one of 'INSTRUCTOR', 'STUDENT', or 'ADMINISTRATOR'.

    The `role` can be used for permission checks and to separate instructor
    behavior (creating courses) from student behavior (enrolling, viewing).
    """
    role = models.ForeignKey(
        RoleLookup,
        on_delete=models.PROTECT,
        related_name='users'
    )

class Course(models.Model):
    """A course created by an instructor.

    Fields:
    - `title` (str): human-readable course title.
    - `description` (text): full course description.
    - `instructor` (ForeignKey->User): the user who teaches the course.
      Uses `related_name='instructed_courses'` so you can access
      `some_user.instructed_courses.all()` for reverse lookup.
    - `created_at`, `updated_at` (datetime): timestamps maintained by Django.
    """

    title = models.CharField(max_length=200)
    description = models.TextField()
    instructor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='instructed_courses'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Module(models.Model):
    """A numbered module that belongs to a course.

    Fields:
    - `title` (str): module title.
    - `course` (ForeignKey->Course): the parent course. Reverse access via
      `course.modules` because of `related_name='modules'`.
    - `module_number` (int): 1-based ordering index within the course.

    Meta:
    - `ordering = ['module_number']` ensures modules are returned in order.
    - `unique_together = ('course', 'module_number')` prevents duplicate
      module numbers within the same course.
    """

    title = models.CharField(max_length=200)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='modules'
    )
    module_number = models.IntegerField()

    class Meta:
        ordering = ['module_number']
        unique_together = ('course', 'module_number')

    def __str__(self):
        return f"{self.course.title} - Module {self.module_number}"


class Lesson(models.Model):
    """A lesson inside a module.

    Fields:
    - `title` (str): lesson title.
    - `content` (text): lesson content (plain text or HTML).
    - `module` (ForeignKey->Module): parent module. Reverse access via
      `module.lessons` because of `related_name='lessons'`.
    - `lesson_number` (int): order of the lesson inside the module.

    Meta:
    - `ordering = ['lesson_number']` ensures lessons return in order.
    - `unique_together = ('module', 'lesson_number')` prevents duplicate
      lesson numbers within a module.
    """

    title = models.CharField(max_length=200)
    content = models.TextField()
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    lesson_number = models.IntegerField()

    class Meta:
        ordering = ['lesson_number']
        unique_together = ('module', 'lesson_number')

    def __str__(self):
        return self.title