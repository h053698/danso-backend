from asgiref.sync import sync_to_async
from django.http import HttpResponse, JsonResponse
from rest_framework.exceptions import AuthenticationFailed

from user.models import GameUser

__all__ = [
    "login_code_to_user",
]


async def login_code_to_user(login_code: str) -> GameUser:
    user_filter = sync_to_async(
        lambda: list(GameUser.objects.filter(login_code=login_code))
    )
    users = await user_filter()
    if len(users) == 0:
        raise AuthenticationFailed("로그인이 필요합니다.")
    return users[0]