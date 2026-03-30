from django.urls import path
from . import views
urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('token/', views.CookieTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', views.CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('courses/', views.CourseView.as_view(), name='course-list-create'),
    path('courses/<int:course_id>/', views.CourseDetailView.as_view(), name='course-detail'),
]