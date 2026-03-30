from .models import User,Course, Module, Lesson, RoleLookup
from enrollment.models import Enrollment
from rest_framework import serializers


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class RegisterSerializer(serializers.ModelSerializer):
    role = serializers.CharField(write_only=True)  # Accept string role_num from frontend
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_username(self, value):
        if not value.strip():
            raise serializers.ValidationError("Username cannot be blank.")

        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        
        return value
    def validate_email(self, value):
        if not value.strip():
            raise serializers.ValidationError("Email cannot be blank.")
        
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        
        return value
    
    def validate_role(self, value):
        # Frontend contract: send string role_num (e.g., 'INST', 'STUD', 'ADMIN')
        raw_role = str(value).strip() if value else None
        if not raw_role:
            raise serializers.ValidationError("Role is required.")

        # Validate against known role keys in the database
        role_obj = RoleLookup.objects.filter(role_num=raw_role).first()
        if not role_obj:
            valid_roles = ", ".join([r.role_num for r in RoleLookup.objects.all()])
            raise serializers.ValidationError(f"Role must be one of: {valid_roles}")
        return raw_role  # Return the string key
    
    def create(self, validated_data):
        # Convert role string to RoleLookup instance
        role_num = validated_data.pop('role')
        role_obj = RoleLookup.objects.get(role_num=role_num)
        user = User.objects.create_user(
            **validated_data,
            role=role_obj
        )
        return user
        
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    def validate(self, data):
        if not data['username'].strip():
            raise serializers.ValidationError("Username cannot be blank.")

        if not data['password'].strip():
            raise serializers.ValidationError("Password cannot be blank.")

        user = User.objects.filter(username=data['username']).first()
        if not user:
            raise serializers.ValidationError("User with this username does not exist.")
        return data

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'description','created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title cannot be blank.")
        return value

    def validate_description(self, value):
        if not value.strip():
            raise serializers.ValidationError("Description cannot be blank.")
        return value


class CourseListSerializer(serializers.ModelSerializer):
    instructor = UserSummarySerializer(read_only=True)
    enrolled_students = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'description',
            'created_at',
            'updated_at',
            'instructor',
            'enrolled_students',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'instructor', 'enrolled_students']

    def get_enrolled_students(self, obj):
        qs = User.objects.filter(
            enrollments__course=obj,
            enrollments__status=Enrollment.Status.ACTIVE,
        ).distinct()
        return UserSummarySerializer(qs, many=True).data
    
class CourseDetailSerializer(serializers.ModelSerializer):
    instructor = UserSummarySerializer(read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'created_at', 'updated_at', 'instructor']
        read_only_fields = ['id', 'created_at', 'updated_at', 'instructor']
        extra_kwargs = {
            'title': {'required': False},
            'description': {'required': False},
        }

    def validate(self, attrs):
        title = attrs.get('title')
        description = attrs.get('description')
        if title is not None and not title.strip():
            raise serializers.ValidationError({'title': 'Title cannot be blank.'})

        if description is not None and not description.strip():
            raise serializers.ValidationError({'description': 'Description cannot be blank.'})
        return attrs
    