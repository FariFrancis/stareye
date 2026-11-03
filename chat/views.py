import json

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from date.services import ChatAccessError, get_chat_match

from .models import MAX_MESSAGE_LENGTH, Message

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


def _forbidden():
    return JsonResponse({"error": "Chat not available"}, status=403)


def _serialize(message):
    return {
        "id": message.id,
        "sender": message.sending_user.user.username,
        "message": "[deleted]" if message.is_deleted else message.message,
        "created": message.creation_date.isoformat(),
        "is_deleted": message.is_deleted,
    }


@login_required
def chat_home(request):
    return redirect("matches")


@login_required
def chat_room(request, match_id):
    try:
        match, me, other = get_chat_match(request.user, match_id)
    except ChatAccessError:
        raise Http404
    config = {
        "matchId": match.pk,
        "me": me.user.username,
        "historyUrl": reverse("get-message", args=[match.pk]),
        "wsPath": f"/ws/chat/{match.pk}/",
        "maxLength": MAX_MESSAGE_LENGTH,
    }
    return render(request, "chat/room.html", {"other": other, "chat_config": config})


@login_required
@require_http_methods(["GET"])
def get_message(request, match_id):
    try:
        match, _me, _other = get_chat_match(request.user, match_id)
    except ChatAccessError:
        return _forbidden()

    try:
        limit = min(max(int(request.GET.get("limit", DEFAULT_PAGE_SIZE)), 1), MAX_PAGE_SIZE)
        before = request.GET.get("before")
        before = int(before) if before else None
    except ValueError:
        return JsonResponse({"error": "limit and before must be integers"}, status=400)

    queryset = Message.objects.filter(match=match).select_related("sending_user__user")
    if before is not None:
        queryset = queryset.filter(id__lt=before)

    page = list(queryset.order_by("-id")[: limit + 1])
    has_more = len(page) > limit
    page = list(reversed(page[:limit]))

    return JsonResponse({
        "messages": [_serialize(m) for m in page],
        "has_more": has_more,
        "next_before": page[0].id if page and has_more else None,
    })


@login_required
@require_http_methods(["POST"])
def send_message(request, match_id):
    try:
        match, me, _other = get_chat_match(request.user, match_id)
    except ChatAccessError:
        return _forbidden()

    try:
        body = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    content = body.get("message") if isinstance(body, dict) else None

    if not isinstance(content, str) or not content.strip():
        return JsonResponse({"error": "Message content required"}, status=400)
    content = content.strip()
    if len(content) > MAX_MESSAGE_LENGTH:
        return JsonResponse(
            {"error": f"Message must be at most {MAX_MESSAGE_LENGTH} characters"}, status=400
        )

    message = Message.objects.create(match=match, sending_user=me, message=content)
    return JsonResponse(_serialize(message), status=201)


@login_required
@require_http_methods(["PATCH"])
def delete_message(request, message_id):
    message = get_object_or_404(
        Message.objects.select_related("sending_user__user"), id=message_id
    )

    # Only the sender can delete
    if message.sending_user.user_id != request.user.id:
        return JsonResponse({"error": "You cannot delete this message"}, status=403)

    message.is_deleted = True
    message.deleted_at = timezone.now()
    message.save(update_fields=["is_deleted", "deleted_at"])

    return JsonResponse({
        "status": "deleted",
        "id": message.id,
        "deleted_at": message.deleted_at.isoformat(),
    })
