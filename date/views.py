from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from .models import UserProfile, Match
from .data import profiles


def home(request):
    return render(request, "home.html")

def profile_list(request):
    return render(request, "date/profile_list.html", {"profiles": profiles})

@login_required
@require_http_methods(["POST"])
def create_match(request, user_id):
    matcher = get_object_or_404(UserProfile, user=request.user)
    matchee = get_object_or_404(UserProfile, user__id=user_id)

    if matcher == matchee:
        return JsonResponse({"error": "You cannot match yourself"}, status=400)

    if Match.objects.filter(matcher=matcher, matchee=matchee).exists() or \
       Match.objects.filter(matcher=matchee, matchee=matcher).exists():
        return JsonResponse({"error": "Match already exists"}, status=400)

    match = Match.objects.create(
        matcher=matcher,
        matchee=matchee,
        status="pending"
    )

    return JsonResponse({
        "status": "match_created",
        "match_id": match.id
    }, status=201)

@login_required
@require_http_methods(["POST"])
def accept_match(request, match_id):
    match = get_object_or_404(Match, id=match_id)

    # Only the matchee can accept
    if match.matchee.user != request.user:
        return JsonResponse({"error": "You cannot accept this match"}, status=403)

    if match.status != "pending":
        return JsonResponse({"error": "Match is not pending"}, status=400)

    match.status = "accepted"
    match.save()

    return JsonResponse({
        "status": "accepted",
        "match_id": match.id
    })

@login_required
def profile_detail(request, profile_id):
    profile = get_object_or_404(UserProfile, user__id=profile_id)

    return render(request, "date/profile_detail.html", {
        "profile": profile
    })

@login_required
def feed(request):
    current_profile = get_object_or_404(UserProfile, user=request.user)

    profiles = UserProfile.objects.exclude(pk=current_profile.pk)

    return render(request, "feed.html", {
        "profiles": profiles
    })

@login_required
def edit_profile(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == "POST":
        profile.user_birth_date = request.POST.get("birth_date")
        profile.user_Descrip = request.POST.get("description")
        profile.user_Location = request.POST.get("location")
        profile.gender = request.POST.get("gender")
        profile.preference = request.POST.get("preference")
        profile.hair = request.POST.get("hair")
        profile.ethnic = request.POST.get("ethnic")
        profile.rel_History = request.POST.get("rel_History")
        profile.education = request.POST.get("education")
        profile.occupation = request.POST.get("occupation")
        profile.height = request.POST.get("height")
        profile.save()

        return redirect(f"/profile/{profile.user.id}/")

    return render(request, "profile_edit.html", {"profile": profile})

# Optional 
# @login_required
# @require_http_methods(["POST"])
# def block_user(request, user_id):
#     blocker = get_object_or_404(UserProfile, user=request.user)
#     blocked = get_object_or_404(UserProfile, user__id=user_id)

#     if blocker == blocked:
#         return JsonResponse({"error": "You cannot block yourself"}, status=400)

#     Block.objects.get_or_create(blocker=blocker, blocked=blocked)

#     return JsonResponse({"status": "blocked", "user": blocked.user.username})

# Optional and used for full production versions
# @login_required
# @require_http_methods(["POST"])
# def unblock_user(request, user_id):
#     blocker = get_object_or_404(UserProfile, user=request.user)
#     blocked = get_object_or_404(UserProfile, user__id=user_id)

#     Block.objects.filter(blocker=blocker, blocked=blocked).delete()

#     return JsonResponse({"status": "unblocked", "user": blocked.user.username})