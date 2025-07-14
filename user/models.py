import string
import random

from django.db import models


class GameUser(models.Model):
    id = models.AutoField(primary_key=True)
    nickname = models.CharField(max_length=150)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    login_code = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "유저"
        verbose_name_plural = "유저"

    def __str__(self):
        return f"GameUser(id={self.id}, nickname={self.nickname}, username={self.username})"
