# from .models import Block, UserProfile

# def can_users_chat(match, user):
#     # Only participants
#     if user not in [match.matcher.user, match.matchee.user]:
#         return False, "You are not part of this match."

#     # Block check
#     user_profile = UserProfile.objects.get(user=user)
#     other_profile = match.matcher if match.matchee.user == user else match.matchee

#     # If either user blocked the other
#     if Block.objects.filter(blocker=user_profile, blocked=other_profile).exists():
#         return False, "You blocked this user."

#     if Block.objects.filter(blocker=other_profile, blocked=user_profile).exists():
#         return False, "This user blocked you."

#     # Match must be accepted
#     if match.status != "accepted":
#         return False, f"Match status is '{match.status}', chat not allowed."

#     return True, None

# from date.models import Block, UserProfile

# def is_blocked(user_a, user_b):
#     """
#     Returns True if either user blocked the other.
#     """
#     profile_a = UserProfile.objects.get(user=user_a)
#     profile_b = UserProfile.objects.get(user=user_b)

#     if Block.objects.filter(blocker=profile_a, blocked=profile_b).exists():
#         return True


#     if Block.objects.filter(blocker=profile_b, blocked=profile_a).exists():
#         return True

#     return False
