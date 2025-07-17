from django.db import models
from rest_framework.relations import ManyRelatedField
from asgiref.sync import sync_to_async

from user.models import GameUser  # User 모델 import


class SentencePack(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    original_author = models.CharField(
        max_length=255, blank=True, null=True
    )  # 원작자 이름
    author: GameUser = models.ForeignKey(
        GameUser, on_delete=models.CASCADE, related_name="sentences"
    )
    sentences = models.TextField()
    LEVEL_CHOICES = [
        ("A", "상"),
        ("B", "중상"),
        ("C", "중"),
        ("D", "중하"),
        ("E", "하"),
    ]

    level = models.CharField(max_length=1, choices=LEVEL_CHOICES)
    image_url = models.URLField(blank=True, null=True)  # S3/R2 업로드된 파일의 URL 저장
    # image_id와 image_file 필드는 삭제
    likes: ManyRelatedField["SentencePackLike"]

    async def get_total_likes(self):
        return await sync_to_async(self.likes.count)()

    class Meta:
        verbose_name = "문장세트"
        verbose_name_plural = "문장세트들"

    def get_level_display_korean(self):
        return dict(self.LEVEL_CHOICES).get(self.level, "")

    def __str__(self):
        return f"SentencePack(id={self.id}, name={self.name}, author={self.author.nickname if self.author else 'Unknown'})"


class SentencePackLike(models.Model):
    user = models.ForeignKey(
        GameUser,
        on_delete=models.CASCADE,
        related_name="likes_given",
        verbose_name="좋아요 누른 사용자",
    )
    pack = models.ForeignKey(
        SentencePack,
        on_delete=models.CASCADE,
        related_name="likes",
        verbose_name="좋아요 받은 문장세트",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="좋아요 누른 시각"
    )

    def __str__(self):
        return f"{self.user.username} 님이 {self.pack.name} 에 좋아요"

    class Meta:
        unique_together = ("user", "pack")
        verbose_name = "좋아요"
        verbose_name_plural = "좋아요들"


class SentenceLeaderboard(models.Model):
    id = models.AutoField(primary_key=True)
    sentence_pack = models.ForeignKey(
        SentencePack, on_delete=models.CASCADE, related_name="leaderboards"
    )
    player = models.ForeignKey(
        GameUser, on_delete=models.CASCADE, related_name="game_scores"
    )
    score = models.IntegerField(default=0)

    class Meta:
        unique_together = ("sentence_pack", "player")
        verbose_name = "리더보드값"
        verbose_name_plural = "리더보드"

    def __str__(self):
        return f"Leaderboard: {self.sentence_pack.name} - {self.player.nickname}: {self.score}점"
