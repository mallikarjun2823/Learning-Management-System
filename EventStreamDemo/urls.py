from django.urls import path
from .views import render_event_stream
urlpatterns = [
    path('event-stream/', render_event_stream, name='event_stream'),
]

