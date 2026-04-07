from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Profile
from django.conf import settings
import os


class RegisterView(APIView):
    """
    Handles profile registration with file upload (avatar + resume)
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        name = request.data.get('name')
        email = request.data.get('email')
        age = request.data.get('age')

        avatar = request.FILES.get('avatar')
        resume = request.FILES.get('resume')

        # Validation
        if not name or not email or not age:
            return Response(
                {'error': 'Name, email, and age are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if Profile.objects.filter(email=email).exists():
            return Response(
                {'error': 'Email already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create profile
        profile = Profile.objects.create(
            username=name,
            name=name,
            email=email,
            age=age,
            avatar=avatar,
            resume=resume
        )
        print(f"Profile created: {profile}")
        return Response(
            {
                'message': 'Profile created successfully.',
                'profile_id': profile.id
            },
            status=status.HTTP_201_CREATED
        )


class StreamResumeView(APIView):
    """
    Streams resume file efficiently (for download/viewing)
    """

    def get(self, request, id):
        profile = Profile.objects.filter(id=id).first()

        if not profile or not profile.resume:
            return Response(
                {'error': 'Resume not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        import mimetypes

        # Resolve on-disk path and handle accidental double-'media' prefixes
        original_path = profile.resume.path
        media_root = str(settings.MEDIA_ROOT)
        # If the stored path includes an extra 'media' segment (media/media/...), fix it
        duplicate_media_prefix = os.path.join(media_root, 'media')
        file_path = original_path
        if file_path.startswith(duplicate_media_prefix + os.sep):
            file_path = file_path.replace(duplicate_media_prefix + os.sep, media_root + os.sep, 1)

        # If file still missing, try constructing path from MEDIA_ROOT + the field name
        if not os.path.exists(file_path):
            candidate = profile.resume.name
            if candidate.startswith('media/'):
                candidate = candidate[len('media/'):]
            alt_path = os.path.join(media_root, candidate)
            if os.path.exists(alt_path):
                file_path = alt_path

        if not os.path.exists(file_path):
            return Response({'error': 'File not found on disk.'}, status=status.HTTP_404_NOT_FOUND)

        def file_iterator(file_path_inner, chunk_size=8192):
            with open(file_path_inner, 'rb') as f:
                while chunk := f.read(chunk_size):
                    yield chunk

        # Guess the correct MIME type for the file
        mime_type, _ = mimetypes.guess_type(file_path)
        content_type = mime_type or 'application/octet-stream'

        response = StreamingHttpResponse(
            file_iterator(file_path),
            content_type=content_type
        )

        # For images, prefer inline display; otherwise force download
        if content_type.startswith('image/'):
            response['Content-Disposition'] = f'inline; filename="{profile.resume.name}"'
        else:
            response['Content-Disposition'] = f'attachment; filename="{profile.resume.name}"'

        try:
            response['Content-Length'] = str(os.path.getsize(file_path))
        except Exception:
            pass

        response['X-Accel-Buffering'] = 'no'  # Disable buffering for Nginx

        return response