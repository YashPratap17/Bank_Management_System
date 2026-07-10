import json
import numpy as np
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from .models import FaceProfile
from numpy.linalg import norm   # already imported, will use for cosine

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

def cosine_similarity(a, b):
    """Return cosine similarity between two vectors."""
    return np.dot(a, b) / (norm(a) * norm(b))

# @csrf_exempt  # use CSRF token in production, but for AJAX it's fine with token in header
# def api_face_login(request):
#     """Login by matching face descriptor using cosine similarity."""
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             descriptor = data.get('descriptor')
#             if not descriptor or len(descriptor) != 128:
#                 return JsonResponse({'success': False, 'error': 'Invalid descriptor'})
#             input_vec = np.array(descriptor)
#             best_match = None
#             best_similarity = -1.0       # cosine similarity ranges from -1 to 1
#             threshold = 0.7              # 0.7 works well; higher = stricter

#             # Compare with all stored face profiles
#             for profile in FaceProfile.objects.select_related('user').all():
#                 stored_vec = np.array(profile.get_descriptor())
#                 sim = cosine_similarity(input_vec, stored_vec)
#                 if sim > threshold and sim > best_similarity:
#                     best_similarity = sim
#                     best_match = profile.user

#             if best_match:
#                 login(request, best_match)
#                 return JsonResponse({'success': True, 'redirect': '/'})
#             else:
#                 return JsonResponse({'success': False, 'error': 'Face not recognized'})
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': str(e)})
#     return JsonResponse({'success': False, 'error': 'Invalid method'})
# @csrf_exempt
# def api_face_login(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             descriptor = data.get('descriptor')
#             if not descriptor or len(descriptor) != 128:
#                 return JsonResponse({'success': False, 'error': 'Invalid descriptor'})

#             input_vec = np.array(descriptor)
#             best_match = None
#             best_similarity = -1.0
#             profiles_checked = 0

#             for profile in FaceProfile.objects.select_related('user').all():
#                 stored_vec = np.array(profile.get_descriptor())
#                 sim = cosine_similarity(input_vec, stored_vec)
#                 profiles_checked += 1
#                 if sim > best_similarity:
#                     best_similarity = sim
#                     best_match = profile.user

#             # Diagnostic info (remove in production)
#             return JsonResponse({
#                 'success': False,
#                 'error': f'Best similarity: {best_similarity:.4f}, Profiles checked: {profiles_checked}, Threshold needed: 0.7'
#             })
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': str(e)})
#     return JsonResponse({'success': False, 'error': 'Invalid method'})

# @csrf_exempt
# def api_face_login(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             descriptor = data.get('descriptor')
#             if not descriptor or len(descriptor) != 128:
#                 return JsonResponse({'success': False, 'error': 'Invalid descriptor'})

#             input_vec = np.array(descriptor)
#             best_match = None
#             best_similarity = -1.0
#             threshold = 0.5

#             for profile in FaceProfile.objects.select_related('user').all():
#                 stored_vec = np.array(profile.get_descriptor())
#                 sim = cosine_similarity(input_vec, stored_vec)
#                 if sim > threshold and sim > best_similarity:
#                     best_similarity = sim
#                     best_match = profile.user

#             if best_match:
#                 login(request, best_match)
#                 return JsonResponse({'success': True, 'redirect': '/'})
#             else:
#                 return JsonResponse({'success': False, 'error': 'Face not recognized'})
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': str(e)})
#     return JsonResponse({'success': False, 'error': 'Invalid method'})


# @csrf_exempt
# def api_face_login(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             descriptor = data.get('descriptor')
#             if not descriptor or len(descriptor) != 128:
#                 return JsonResponse({'success': False, 'error': 'Invalid descriptor'})

#             input_vec = np.array(descriptor)
#             best_match = None
#             best_similarity = -1.0
#             profiles_checked = 0

#             for profile in FaceProfile.objects.select_related('user').all():
#                 profiles_checked += 1
#                 try:
#                     stored_vec = np.array(profile.get_descriptor())
#                 except Exception:
#                     return JsonResponse({'success': False, 'error': f'Decryption failed for user {profile.user.username}'})
#                 sim = cosine_similarity(input_vec, stored_vec)
#                 if sim > best_similarity:
#                     best_similarity = sim
#                     best_match = profile.user

#             # Always return diagnostic info (temporary)
#             return JsonResponse({
#                 'success': False,
#                 'error': f'Profiles: {profiles_checked}, Best similarity: {best_similarity:.4f}',
#                 'best_similarity': best_similarity,
#                 'profiles_checked': profiles_checked,
#             })
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': f'Exception: {str(e)}'})
#     return JsonResponse({'success': False, 'error': 'Invalid method'})

# def test_face(request):
#     return JsonResponse({"hello": "world"})

@csrf_exempt
def api_face_login(request):
    # Temporary: accepts both GET and POST for debugging
    try:
        if request.method == 'POST':
            data = json.loads(request.body)
            descriptor = data.get('descriptor')
        else:
            descriptor = None

        if descriptor and len(descriptor) == 128:
            input_vec = np.array(descriptor)
            best_similarity = -1.0
            profiles_checked = 0
            best_match = None

            for profile in FaceProfile.objects.select_related('user').all():
                profiles_checked += 1
                stored_vec = np.array(profile.get_descriptor())
                sim = cosine_similarity(input_vec, stored_vec)
                if sim > best_similarity:
                    best_similarity = sim
                    best_match = profile.user

            return JsonResponse({
                'success': False,
                'error': f'Profiles: {profiles_checked}, Best similarity: {best_similarity:.4f}',
                'method': request.method,
            })

        return JsonResponse({
            'success': False,
            'error': f'No valid descriptor. Method: {request.method}',
            'method': request.method,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Exception: {str(e)}'})