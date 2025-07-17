import string
import random
import json

from django.db import models


class GameUser(models.Model):
    id = models.AutoField(primary_key=True)
    nickname = models.CharField(max_length=150)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    login_code = models.CharField(max_length=255, blank=True, null=True)
    history = models.TextField(
        blank=True, null=True, default="[]"
    )  # SentencePack ID들을 JSON 배열로 저장
    now = models.IntegerField(blank=True, null=True)  # 현재 진행 중인 SentencePack ID

    class Meta:
        verbose_name = "유저"
        verbose_name_plural = "유저"

    def __str__(self):
        return f"GameUser(id={self.id}, nickname={self.nickname}, username={self.username})"

    def add_to_history(self, sentence_pack_id):
        """SentencePack ID를 history에 추가"""
        try:
            history_list = json.loads(self.history) if self.history else []
            if sentence_pack_id not in history_list:
                history_list.append(sentence_pack_id)
                self.history = json.dumps(history_list)
                self.save()
        except (json.JSONDecodeError, ValueError):
            # history가 잘못된 JSON인 경우 초기화
            self.history = json.dumps([sentence_pack_id])
            self.save()

    def get_history(self):
        """history에서 SentencePack ID 리스트 반환"""
        try:
            return json.loads(self.history) if self.history else []
        except (json.JSONDecodeError, ValueError):
            return []

    def clear_history(self):
        """history 초기화"""
        self.history = json.dumps([])
        self.save()
