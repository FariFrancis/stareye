from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Message
from date.models import Match, UserProfile
# from date.utils import can_users_chat
import json
import datetime


@login_required
@require_http_methods(["GET"])
def get_message(request, match_id):
    match = get_object_or_404(Match, id=match_id)

    # allowed, error = can_users_chat(match, request.user)
    # if not allowed:
    #     return JsonResponse({"error": error}, status=403)

    # Pagination
    # limit = int(request.GET.get("limit", 50))
    # offset = int(request.GET.get("offset", 0))

    messages = Message.objects.filter(match=match).order_by("creation_date")
    # paginated = messages[offset:offset + limit]

    data = [
        {
            "id": m.id,
            "sender": m.sending_user.user.username,
            "message": "[deleted]" if m.is_deleted else m.message,
            "created": m.creation_date.isoformat(),
            "is_deleted": m.is_deleted,
        }
        for m in messages
    ]

    return JsonResponse({
        "messages": data,
        # "next_offset": offset + limit,
        # "has_more": (offset + limit) < messages.count()
    })



@login_required
@require_http_methods(["POST"])
def send_message(request, match_id):
    match = get_object_or_404(Match, id=match_id)

    # Authentication hardening
    # allowed, error = can_users_chat(match, request.user)
    # if not allowed:
    #     return JsonResponse({"error": error}, status=403)

    body = json.loads(request.body.decode("utf-8"))
    content = body.get("message")

    if not content:
        return JsonResponse({"error": "Message content required"}, status=400)

    sender_profile = get_object_or_404(UserProfile, user=request.user)

    message = Message.objects.create(
        match=match,
        sending_user=sender_profile,
        message=content
    )

    return JsonResponse({
        "id": message.id,
        "sender": message.sending_user.user.username,
        "message": message.message,
        "created": message.creation_date.isoformat(),
    }, status=201)



@login_required
@require_http_methods(["PATCH"])
def delete_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)

    # Only sender can delete
    if message.sending_user.user != request.user:
        return JsonResponse({"error": "You cannot delete this message"}, status=403)

    message.is_deleted = True
    message.deleted_at = datetime.datetime.now()
    message.save()

    return JsonResponse({
        "status": "deleted",
        "id": message.id,
        "deleted_at": message.deleted_at.isoformat(),
    })



def chat_home(request):
    return render(request, "chat/home.html")

def message(request):
    return render(request, "chat/message.html")
