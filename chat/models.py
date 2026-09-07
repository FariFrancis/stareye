from django.db import models
from django.contrib.auth.models import User
# Create your models here.
class Message(models.Model):
    id = models.IntegerField(max_length=30, primary_key= True)
    rec_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rec_user")
    sending_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sending_user")
    message = models.TextField(max_length = 500)
    creation_date = models.DateTimeField("Creation date")
