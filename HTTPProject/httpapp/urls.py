from . import views
from django.urls import path

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/<int:id>/', views.StreamResumeView.as_view(), name='stream_resume'),
]
