import json
import numpy as np
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from .models import FaceProfile

User = get_user_model()

@login_required
def register_face(request):
    """Page with webcam to capture face descriptor."""
    return render(request, 'dashboard/register_face.html')

@login_required
def api_register_face(request):
    """Endpoint to receive and store encrypted face descriptor."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            descriptor = data.get('descriptor')
            if not descriptor or len(descriptor) != 128:
                return JsonResponse({'success': False, 'error': 'Invalid descriptor'})
            profile, _ = FaceProfile.objects.get_or_create(user=request.user)
            profile.set_descriptor(descriptor)
            profile.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid method'})

@csrf_exempt  # use CSRF token in production, but for AJAX it's fine with token in header
def api_face_login(request):
    """Login by matching face descriptor."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            descriptor = data.get('descriptor')
            if not descriptor or len(descriptor) != 128:
                return JsonResponse({'success': False, 'error': 'Invalid descriptor'})
            input_vec = np.array(descriptor)
            best_match = None
            best_distance = 1.0
            threshold = 0.6  # typical face-api threshold (lower is stricter)
            # Compare with all stored face profiles
            for profile in FaceProfile.objects.select_related('user').all():
                stored_vec = np.array(profile.get_descriptor())
                distance = np.linalg.norm(input_vec - stored_vec)
                if distance < threshold and distance < best_distance:
                    best_distance = distance
                    best_match = profile.user
            if best_match:
                login(request, best_match)
                return JsonResponse({'success': True, 'redirect': '/'})
            else:
                return JsonResponse({'success': False, 'error': 'Face not recognized'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid method'})

