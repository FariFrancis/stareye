from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

# from recommend import events
# from recommend.models import Swipe

from . import geo, services
from .forms import PhotoUploadForm, ProfileForm
from .models import Match, ProfileImage, UserProfile
from .photos import MAX_PHOTOS


def _wants_json(request):
    return (
        "application/json" in request.headers.get("Accept", "")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )


def _respond(request, ok, message, payload=None, status=200,
             redirect_to="feed", redirect_args=()):

    if _wants_json(request):
        body = dict(payload or {}) if ok else {"error": message}
        return JsonResponse(body, status=status)
    (messages.success if ok else messages.error)(request, message)
    return redirect(redirect_to, *redirect_args)


def home(request):
    return render(request, "home.html")

#Feed content
@login_required
def feed(request):
    me = services.get_profile(request.user)
    complete = me.is_complete()
    ranked = services.get_recommendations(me) if complete else []
    return render(request, "feed.html", {
        "profile": me,
        "ranked": ranked,
        "profile_complete": complete,
    })


@login_required
def matches(request):
    me = services.get_profile(request.user)
    hidden = services.blocked_ids(me)
    rows = (
        Match.objects.filter(Q(matcher=me) | Q(matchee=me))
        .select_related("matcher__user", "matchee__user")
        .order_by("-matched_at")
    )

    incoming, outgoing, accepted = [], [], []
    for match in rows:
        other = match.matchee if match.matcher_id == me.pk else match.matcher
        if other.pk in hidden:
            continue
        entry = {"match": match, "other": other}
        if match.status == Match.ACCEPTED:
            accepted.append(entry)
        elif match.status == Match.PENDING:
            (incoming if match.matchee_id == me.pk else outgoing).append(entry)

    return render(request, "matches.html", {
        "incoming": incoming,
        "outgoing": outgoing,
        "accepted": accepted,
    })

#Matching logic
@login_required
@require_POST
def create_match(request, user_id):
    me = services.get_profile(request.user)
    target = get_object_or_404(UserProfile, user__id=user_id)
    try:
        match, mutual = services.request_match(me, target)
    except services.MatchError as exc:
        return _respond(request, False, exc.message, status=exc.status)

    if mutual:
        return _respond(
            request, True, f"It's a match with {target.user.username}!",
            {"status": "accepted", "match_id": match.id}, redirect_to="matches",
        )
    return _respond(
        request, True, f"Request sent to {target.user.username}.",
        {"status": "match_created", "match_id": match.id}, status=201,
    )


def _respond_to_match(request, match_id, accept):
    me = services.get_profile(request.user)
    try:
        match = services.respond_to_match(me, match_id, accept)
    except services.MatchError as exc:
        return _respond(request, False, exc.message, status=exc.status,
                        redirect_to="matches")
    state = "accepted" if accept else "rejected"
    return _respond(request, True, f"Request {state}.",
                    {"status": state, "match_id": match.id}, redirect_to="matches")

#Accepting and rejecting matches
@login_required
@require_POST
def accept_match(request, match_id):
    return _respond_to_match(request, match_id, accept=True)


@login_required
@require_POST
def reject_match(request, match_id):
    return _respond_to_match(request, match_id, accept=False)

#Blocking users
@login_required
@require_POST
def block_user(request, user_id):
    me = services.get_profile(request.user)
    target = get_object_or_404(UserProfile, user__id=user_id)
    try:
        services.block_user(me, target)
    except services.MatchError as exc:
        return _respond(request, False, exc.message, status=exc.status)
    return _respond(request, True, f"You blocked {target.user.username}.",
                    {"status": "blocked", "user": target.user.username})

#Unblocking users
@login_required
@require_POST
def unblock_user(request, user_id):
    me = services.get_profile(request.user)
    target = get_object_or_404(UserProfile, user__id=user_id)
    services.unblock_user(me, target)
    return _respond(request, True, f"You unblocked {target.user.username}.",
                    {"status": "unblocked", "user": target.user.username},
                    redirect_to="profile-detail", redirect_args=(user_id,))

#Profile details and specifications

@login_required
def my_profile(request):
    return redirect("profile-detail", profile_id=request.user.id)


@login_required
def profile_detail(request, profile_id):
    profile = get_object_or_404(
        UserProfile.objects.select_related("user").prefetch_related("images"),
        user__id=profile_id,
    )
    me = services.get_profile(request.user)
    is_me = profile.pk == me.pk

    i_blocked = False
    if not is_me:
        i_blocked = services.has_blocked(me, profile)
        # Hide the profile from anyone who has been blocked by its owner.
        if services.is_blocked_between(me, profile) and not i_blocked:
            raise Http404

    return render(request, "profile_detail.html", {
        "profile": profile,
        "is_me": is_me,
        "i_blocked": i_blocked,
    })


@login_required
def edit_profile(request):
    profile = services.get_profile(request.user)
    form = ProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile saved.")
        return redirect("profile-detail", profile_id=request.user.id)
    return render(request, "profile_edit.html", {"form": form, "profile": profile})

#Photo components
@login_required
def photos(request):
    profile = services.get_profile(request.user)
    if request.method == "POST":
        form = PhotoUploadForm(request.POST, request.FILES)
        if profile.images.count() >= MAX_PHOTOS:
            messages.error(request, f"You can have at most {MAX_PHOTOS} photos. Delete one to add another.")
        elif form.is_valid():
            ProfileImage.objects.create(user=profile, image=form.cleaned_data["image"])
            messages.success(request, "Photo added.")
            return redirect("photos")
    else:
        form = PhotoUploadForm()
    return render(request, "photos.html", {
        "photos": list(profile.images.all()), "form": form, "limit": MAX_PHOTOS,
    })


@login_required
@require_POST
def photo_delete(request, photo_id):
    photo = get_object_or_404(ProfileImage, pk=photo_id, user=services.get_profile(request.user))
    photo.image.delete(save=False)  # remove the file as well as the row
    photo.delete()
    messages.success(request, "Photo deleted.")
    return redirect("photos")

#Location components
@login_required
def location(request):
    profile = services.get_profile(request.user)
    if request.method == "POST":
        try:
            services.set_location(profile, request.POST.get("latitude"), request.POST.get("longitude"))
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Location updated.")
        return redirect("location")
    return render(request, "location.html", {"has_location": profile.latitude is not None})


@login_required
@require_POST
def clear_location(request):
    profile = services.get_profile(request.user)
    profile.latitude = profile.longitude = None
    profile.save(update_fields=["latitude", "longitude", "updated_at"])
    messages.success(request, "Your location was removed.")
    return redirect("location")
