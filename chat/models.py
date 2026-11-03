from django.db import models

MAX_MESSAGE_LENGTH = 500


class Message(models.Model):
    match = models.ForeignKey(
        'date.Match',
        on_delete=models.CASCADE,
        related_name="messages"
    )
    class Meta:
        indexes = [
            models.Index(fields=["match", "creation_date"]),
        ]
    sending_user = models.ForeignKey('date.UserProfile', on_delete=models.CASCADE, related_name="messages_sent")
    message = models.TextField(max_length=MAX_MESSAGE_LENGTH)
    creation_date = models.DateTimeField("Creation date", auto_now_add=True)

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        if self.is_deleted:
            return f"{self.sending_user.user.username}: [deleted]"
        return f"{self.sending_user.user.username}: {self.message[:20]}"
