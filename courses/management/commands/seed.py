from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from courses.models import Course, Module, Lesson, RoleLookup
from enrollment.models import Enrollment


class Command(BaseCommand):
    help = "Seed the database with example Users, Courses, Modules and Lessons."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing seeded objects before creating new ones.",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        if options["clear"]:
            self.stdout.write("Clearing existing seeded data...")
            # remove lessons, modules, courses and example users (safe narrow delete)
            Lesson.objects.all().delete()
            Module.objects.all().delete()
            Course.objects.all().delete()
            User.objects.filter(username__in=["instructor1", "student1", "admin"]).delete()

        with transaction.atomic():
            # Ensure RoleLookup rows exist with string keys
            RoleLookup.objects.get_or_create(role_num="INST", defaults={"role_name": "INSTRUCTOR"})
            RoleLookup.objects.get_or_create(role_num="STUD", defaults={"role_name": "STUDENT"})
            RoleLookup.objects.get_or_create(role_num="ADMIN", defaults={"role_name": "ADMINISTRATOR"})

            instructor_role = RoleLookup.objects.get(role_num="INST")
            student_role = RoleLookup.objects.get(role_num="STUD")
            admin_role = RoleLookup.objects.get(role_num="ADMIN")

            # Create users
            instructor, created = User.objects.get_or_create(
                username="instructor1",
                defaults={"email": "instructor@example.com", "role": instructor_role},
            )
            if created:
                instructor.set_password("password")
                instructor.save()

            student, created = User.objects.get_or_create(
                username="student1",
                defaults={"email": "student@example.com", "role": student_role},
            )
            if created:
                student.set_password("password")
                student.save()

            admin, created = User.objects.get_or_create(
                username="admin",
                defaults={
                    "email": "admin@example.com",
                    "role": admin_role,
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            if created:
                admin.set_password("password")
                admin.save()

            # Create a sample course
            course, created = Course.objects.get_or_create(
                title="Intro to Testing",
                defaults={
                    "description": "A short sample course created by seed command.",
                    "instructor": instructor,
                },
            )

            # Ensure instructor relation is set if course already existed
            if not created and course.instructor_id != instructor.id:
                course.instructor = instructor
                course.save()

            # Enroll student in the course via Enrollment model
            Enrollment.objects.get_or_create(
                user=student,
                course=course,
                defaults={"status": Enrollment.Status.ACTIVE},
            )

            # Create another course for variety
            course2, _ = Course.objects.get_or_create(
                title="Advanced Python",
                defaults={
                    "description": "Deep dive into Python programming.",
                    "instructor": instructor,
                },
            )
            # Enroll student in second course too via Enrollment model
            Enrollment.objects.get_or_create(
                user=student,
                course=course2,
                defaults={"status": Enrollment.Status.ACTIVE},
            )

            # Create modules and lessons for first course
            for m in range(1, 4):
                module, _ = Module.objects.get_or_create(
                    course=course,
                    module_number=m,
                    defaults={"title": f"Module {m}"},
                )

                for l in range(1, 4):
                    Lesson.objects.get_or_create(
                        module=module,
                        lesson_number=l,
                        defaults={
                            "title": f"Lesson {l}",
                            "content": f"Sample content for lesson {l} of module {m}.",
                        },
                    )

            # Create modules and lessons for second course
            for m in range(1, 3):
                module, _ = Module.objects.get_or_create(
                    course=course2,
                    module_number=m,
                    defaults={"title": f"Module {m}"},
                )

                for l in range(1, 3):
                    Lesson.objects.get_or_create(
                        module=module,
                        lesson_number=l,
                        defaults={
                            "title": f"Lesson {l}",
                            "content": f"Advanced content for lesson {l} of module {m}.",
                        },
                    )

        self.stdout.write(self.style.SUCCESS("Seeding complete."))
