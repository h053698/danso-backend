from django.contrib import admin
from sentence.models import SentencePack, SentenceLeaderboard, SentencePackLike

admin.site.register(SentencePack)
admin.site.register(SentenceLeaderboard)
admin.site.register(SentencePackLike)
