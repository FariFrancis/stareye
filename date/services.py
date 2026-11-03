#Matching, blocking, chat-access and feed logic
from django.db import transaction
from django.db.models import Q

from recommend.rec import is_compatible, match_score

from .models import Block, Match, UserProfile

CANDIDATE_POOL = 500


class MatchError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


class ChatAccessError(Exception):
    """Raised when a user may not read or write in a match's chat."""


def get_profile(user):
    return UserProfile.objects.get_or_create(user=user)[0]



def blocked_ids(profile):
    pairs = Block.objects.filter(Q(blocker=profile) | Q(blocked=profile)).values_list(
        "blocker_id", "blocked_id"
    )
    ids = set()
    for blocker_id, blocked_id in pairs:
        ids.update((blocker_id, blocked_id))
    ids.discard(profile.pk)
    return ids


def has_blocked(blocker, blocked):
    return Block.objects.filter(blocker=blocker, blocked=blocked).exists()


def is_blocked_between(a, b):
    return Block.objects.filter(
        Q(blocker=a, blocked=b) | Q(blocker=b, blocked=a)
    ).exists()


def block_user(blocker, target):
    if blocker.pk == target.pk:
        raise MatchError("You cannot block yourself")
    Block.objects.get_or_create(blocker=blocker, blocked=target)


def unblock_user(blocker, target):
    Block.objects.filter(blocker=blocker, blocked=target).delete()



@transaction.atomic
def request_match(sender, target):
    # Send a match request. Returns (match, is_mutual).
    # If the person already asked the sender, that request is accepted instead

    if sender.pk == target.pk:
        raise MatchError("You cannot match yourself")
    if is_blocked_between(sender, target):
        raise MatchError("This user is not available", 403)

    reverse = Match.objects.filter(matcher=target, matchee=sender).first()
    if reverse is not None:
        if reverse.status == Match.PENDING:
            reverse.status = Match.ACCEPTED
            reverse.save()
            return reverse, True
        raise MatchError("Match already exists")

    if Match.objects.filter(matcher=sender, matchee=target).exists():
        raise MatchError("Match already exists")

    return Match.objects.create(matcher=sender, matchee=target), False


@transaction.atomic
def respond_to_match(profile, match_id, accept):
    # Accept or reject a pending request addressed
    match = Match.objects.select_for_update().filter(pk=match_id, matchee=profile).first()
    if match is None:
        raise MatchError("Match not found", 404)
    if match.status != Match.PENDING:
        raise MatchError("Match is not pending")
    if is_blocked_between(match.matcher, match.matchee):
        raise MatchError("This user is not available", 403)

    match.status = Match.ACCEPTED if accept else Match.REJECTED
    match.save()
    return match



def get_chat_match(user, match_id):
    # Return (match, my_profile, other_profile) or raise ChatAccessError.

    # Chat is only allowed for the two participants of an accepted match with
    # no block in either direction.
    profile = UserProfile.objects.filter(user=user).first()
    if profile is None:
        raise ChatAccessError("Chat not available")

    match = (
        Match.objects.select_related("matcher__user", "matchee__user")
        .filter(pk=match_id)
        .filter(Q(matcher=profile) | Q(matchee=profile))
        .first()
    )
    if match is None or match.status != Match.ACCEPTED:
        raise ChatAccessError("Chat not available")

    other = match.matchee if match.matcher_id == profile.pk else match.matcher
    if is_blocked_between(profile, other):
        raise ChatAccessError("Chat not available")
    return match, profile, other



def get_recommendations(profile, limit=50):
    # Compatible, not-yet-seen profiles ranked by similarity (best first)
    excluded = {profile.pk} | blocked_ids(profile)
    pairs = Match.objects.filter(Q(matcher=profile) | Q(matchee=profile)).values_list(
        "matcher_id", "matchee_id"
    )
    for matcher_id, matchee_id in pairs:
        excluded.update((matcher_id, matchee_id))

    candidates = (
        UserProfile.objects.exclude(pk__in=excluded)
        .filter(user__is_active=True, user_birth_date__isnull=False)
        .select_related("user")
        .prefetch_related("images")
        .order_by("-updated_at")[:CANDIDATE_POOL]
    )

    scored = [
        (candidate, match_score(profile, candidate))
        for candidate in candidates
        if is_compatible(profile, candidate)
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [
        {"profile": candidate, "score": round(score * 100)}
        for candidate, score in scored[:limit]
    ]
