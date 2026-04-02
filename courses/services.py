from .models import User, Course, Module, Lesson, RoleLookup
from .serializers import RegisterSerializer, LoginSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from enrollment.models import Enrollment
import os
import time

class AuthService:
    def generate_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    def register_user(self, data):
        if User.objects.filter(username=data['username']).exists():
            raise ValueError("Username already exists.")
        if User.objects.filter(email=data['email']).exists():
            raise ValueError("Email already exists.")

        # Serializer returns role as string role_num key (e.g., 'INST', 'STUD')
        role_num = data.get('role')
        if not role_num:
            raise ValueError("Role is required.")

        role_obj = RoleLookup.objects.filter(role_num=role_num).first()
        if not role_obj:
            raise ValueError(f"Role '{role_num}' not found.")

        try:
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                role=role_obj
            )
            user.save()
            return self.generate_tokens_for_user(user)

        except Exception as e:
            raise ValueError(f"Error registering user: {str(e)}")
    
    def login_user(self, data):
        try:
            user = User.objects.get(username=data['username'])
            if user.check_password(data['password']):
                return self.generate_tokens_for_user(user)
            else:
                raise ValueError("Invalid password.")
        except User.DoesNotExist:
            raise ValueError("User does not exist.")
    
    def authenticate_user(self, token):
        try:
            refresh = RefreshToken(token)
            user_id = refresh['user_id']
            user = User.objects.get(id=user_id)
            return user
        except Exception:
            return None
            
class CourseService:

    def list_courses(self, user):
        # Stream the loremtxt.txt file as Server-Sent Events (SSE) so the
        # server keeps the connection open and continuously sends data
        # even if the client doesn't make additional requests.
        def _stream_sse(chunk_size=1024, interval=0.1):
            project_root = os.path.dirname(os.path.dirname(__file__))
            file_path = os.path.join(project_root, 'loremtxt.txt')
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        # SSE event: prefix with 'data:' and end with double newline
                        yield f"data: {chunk}\n\n"
                        time.sleep(interval)
                # After file ends, keep sending heartbeat events indefinitely
                
            except FileNotFoundError:
                raise ValueError("loremtxt.txt not found in project root.")

        return _stream_sse()
        
    
    def create_course(self, user, title, description):
        if not title.strip():
            raise ValueError("Title cannot be blank.")
        if not description.strip():
            raise ValueError("Description cannot be blank.")
        # RoleLookup: instructor uses role_num 'INST'
        user_role_num = getattr(getattr(user, 'role', None), 'role_num', None)
        if not getattr(user, 'is_authenticated', False) or user_role_num != 'INST':
            raise ValueError("Only authenticated instructors can create courses.")
        course = Course.objects.filter(title=title).first()
        if course:
            raise ValueError("A course with this title already exists.")
        course = Course.objects.filter(description=description).first()
        if course:
            raise ValueError("A course with this description already exists.")
        course = Course.objects.create(
            title=title,
            description=description,
            instructor=user
        )
        return Course.objects.select_related('instructor').get(id=course.id)
class CourseDetailService:
    def get_course_detail(self, user, course_id):
        if not getattr(user, 'is_authenticated', False):
            raise ValueError("Authentication required to view course details.")
        
        course = (
            Course.objects.filter(id=course_id)
            .select_related('instructor')
            .prefetch_related('enrollments')
            .first()
        )
        if not course:
            raise ValueError("Course not found.")
        
        user_role_num = getattr(getattr(user, 'role', None), 'role_num', None)
        
        # Check if user is instructor of the course or enrolled student
        if user_role_num == 'INST' and course.instructor_id == user.id:
            return course
        elif user_role_num == 'STUD' and course.enrollments.filter(
            user=user, status=Enrollment.Status.ACTIVE
        ).exists():
            return course
        else:
            raise ValueError("You do not have permission to view this course.")
    def update_course(self, user, course_id, title=None, description=None):
        course = self.get_course_detail(user, course_id)
        user_role_num = getattr(getattr(user, 'role', None), 'role_num', None)
        if user_role_num != 'INST' or course.instructor_id != user.id:
            raise ValueError("Only the instructor of this course can update it.")

        new_title = course.title if title is None else title
        new_description = course.description if description is None else description

        if not new_title.strip():
            raise ValueError("Title cannot be blank.")
        if not new_description.strip():
            raise ValueError("Description cannot be blank.")
        
        is_duplicate_title = Course.objects.filter(title=new_title).exclude(id=course_id).exists()
        is_duplicate_description = Course.objects.filter(description=new_description).exclude(id=course_id).exists()
        if is_duplicate_title:
            raise ValueError("A course with this title already exists.")
        if is_duplicate_description:    
            raise ValueError("A course with this description already exists.")
        course.title = new_title
        course.description = new_description
        course.save()
        return Course.objects.select_related('instructor').get(id=course.id)

    def delete_course(self, user, course_id):
        course = self.get_course_detail(user, course_id)
        user_role_num = getattr(getattr(user, 'role', None), 'role_num', None)
        if user_role_num != 'INST' or course.instructor_id != user.id:
            raise ValueError("Only the instructor of this course can delete it.")
        course.delete()
    