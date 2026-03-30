from django.shortcuts import render
from .models import Course, Module, Lesson
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .services import AuthService, CourseService, CourseDetailService
from .serializers import RegisterSerializer, LoginSerializer, CourseSerializer, CourseDetailSerializer, CourseListSerializer
from .permissions import CoursePermission
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def _set_token_cookie(response, key, token, max_age):
    response.set_cookie(
        key=key,
        value=token,
        max_age=max_age,
        httponly=getattr(settings, "AUTH_COOKIE_HTTP_ONLY", True),
        secure=getattr(settings, "AUTH_COOKIE_SECURE", True),
        samesite=getattr(settings, "AUTH_COOKIE_SAMESITE", "Lax"),
        path="/",
    )


def _clear_token_cookie(response, key):
    response.delete_cookie(
        key=key,
        path="/",
        samesite=getattr(settings, "AUTH_COOKIE_SAMESITE", "Lax"),
    )

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            auth_service = AuthService()
            tokens = auth_service.register_user(serializer.validated_data)
            return Response({"message": "User registered successfully.", "tokens": tokens}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            auth_service = AuthService()
            try:
                tokens = auth_service.login_user(serializer.validated_data)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": "Login successful.", "tokens": tokens}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CookieTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            access = response.data.get("access")
            refresh = response.data.get("refresh")
            if access:
                _set_token_cookie(
                    response,
                    getattr(settings, "AUTH_COOKIE_ACCESS", "access_token"),
                    access,
                    int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
                )
            if refresh:
                _set_token_cookie(
                    response,
                    getattr(settings, "AUTH_COOKIE_REFRESH", "refresh_token"),
                    refresh,
                    int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
                )
        return response


class CookieTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        payload = request.data.copy() if hasattr(request.data, "copy") else {}
        if "refresh" not in payload:
            refresh_cookie_name = getattr(settings, "AUTH_COOKIE_REFRESH", "refresh_token")
            refresh_token = request.COOKIES.get(refresh_cookie_name)
            if refresh_token:
                payload["refresh"] = refresh_token

        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)
        response = Response(serializer.validated_data, status=status.HTTP_200_OK)

        if response.status_code == status.HTTP_200_OK:
            access = response.data.get("access")
            refresh = response.data.get("refresh")
            if access:
                _set_token_cookie(
                    response,
                    getattr(settings, "AUTH_COOKIE_ACCESS", "access_token"),
                    access,
                    int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
                )
            if refresh:
                _set_token_cookie(
                    response,
                    getattr(settings, "AUTH_COOKIE_REFRESH", "refresh_token"),
                    refresh,
                    int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
                )
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response({"message": "Logged out."}, status=status.HTTP_200_OK)
        _clear_token_cookie(response, getattr(settings, "AUTH_COOKIE_ACCESS", "access_token"))
        _clear_token_cookie(response, getattr(settings, "AUTH_COOKIE_REFRESH", "refresh_token"))
        return response

class CourseView(APIView):
    serializer_class = CourseSerializer
    list_serializer_class = CourseListSerializer
    service_class = CourseService
    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'DELETE']:
            return [IsAuthenticated(), CoursePermission()]
        return [AllowAny()]

    def get(self, request):
        service = self.service_class()
        try:
            courses = service.list_courses(request.user)
            serializer = self.list_serializer_class(courses, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            course_service = self.service_class()
            try:
                course = course_service.create_course(request.user, **serializer.validated_data)
                detail_serializer = CourseDetailSerializer(course)
                return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class CourseDetailView(APIView):
    serializer_class = CourseDetailSerializer
    service_class = CourseDetailService
    def get_permissions(self):
        return [IsAuthenticated(), CoursePermission()]    

    def get(self, request, course_id):
        service = self.service_class()
        try:
            course = service.get_course_detail(request.user, course_id)
            serializer = self.serializer_class(course)
            return Response(serializer.data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
    
    def patch(self, request, course_id):
        serializer = self.serializer_class(data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            service = self.service_class()
            try:
                course = service.update_course(
                    request.user,
                    course_id,
                    title=serializer.validated_data.get('title'),
                    description=serializer.validated_data.get('description'),
                )
                detail_serializer = self.serializer_class(course)
                return Response(detail_serializer.data)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, course_id):
        service = self.service_class()
        try:
            service.delete_course(request.user, course_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
