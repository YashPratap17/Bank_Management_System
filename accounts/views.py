import json
import numpy as np
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .models import FaceProfile
from numpy.linalg import norm

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


def euclidean_distance(a, b):
    """Return Euclidean distance between two 128-D face descriptor vectors."""
    return np.linalg.norm(a - b)


@csrf_exempt
def api_face_login(request):
    """
    Login endpoint: receives a 128-float face descriptor, compares it against
    all stored FaceProfile entries using Euclidean distance, and logs in the
    best-matching user if the distance is below MAX_DISTANCE.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})

    try:
        data = json.loads(request.body)
        descriptor = data.get('descriptor')

        if not descriptor or len(descriptor) != 128:
            return JsonResponse({
                'success': False,
                'error': 'Invalid descriptor — must be a list of 128 floats.'
            })

        input_vec = np.array(descriptor, dtype=np.float64)
        best_match = None
        best_distance = float('inf')

        # Euclidean distance threshold.
        # face-api.js default is 0.6. We use 0.55 for slightly stricter security.
        MAX_DISTANCE = 0.55

        for profile in FaceProfile.objects.select_related('user').all():
            try:
                stored_vec = np.array(profile.get_descriptor(), dtype=np.float64)
            except Exception:
                # Skip profiles whose descriptor cannot be decrypted
                # (e.g. registered under a different SECRET_KEY on another environment)
                continue

            dist = euclidean_distance(input_vec, stored_vec)
            if dist < best_distance:
                best_distance = dist
                if dist <= MAX_DISTANCE:
                    best_match = profile.user

        if best_match:
            print(f"Face match SUCCESS: user {best_match.username} (dist={best_distance:.4f} <= {MAX_DISTANCE})")
            # Specify the backend explicitly — required when the user object was
            # not obtained via Django's authenticate() pathway.
            best_match.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, best_match)
            return JsonResponse({'success': True, 'redirect': '/'})
        else:
            print(f"Face match FAIL: best_dist={best_distance:.4f} > {MAX_DISTANCE}")
            return JsonResponse({
                'success': False,
                'error': (
                    f'Face not recognised (best dist: {best_distance:.4f}). '
                    'Try again in better lighting, or re-register your face.'
                ),
            })

    except Exception as e:
        print(f"Face match ERROR: {e}")
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})