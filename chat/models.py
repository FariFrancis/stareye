from django.db import models
from django.contrib.auth.models import User
# Create your models here.
class Message(models.Model):
    match = models.ForeignKey(
        'date.Match',
        on_delete=models.CASCADE,
        related_name="messages"
    )
    # id = models.IntegerField(max_length=30, primary_key= True)
    # rec_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rec_user")
    sending_user = models.ForeignKey('date.UserProfile', on_delete=models.CASCADE, related_name="messages_sent")
    message = models.TextField(max_length = 500)
    creation_date = models.DateTimeField("Creation date", auto_now_add=True)

    def __str__(self):
        return f"{self.sending_user.user.username}: {self.message[:20]}"