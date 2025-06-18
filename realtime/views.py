from adrf.decorators import api_view
from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse
from rest_framework import status
from rest_framework.response import Response

from sentence.models import SentencePack
from user.auth import login_code_to_user
from user.models import GameUser


@api_view(["POST"])
async def match_player(request: HttpRequest):
    login_code = request.headers.get("X-Login-Code", None)
    if not login_code:
        return Response(
            {"error": "Login code is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    user = await login_code_to_user(login_code)
    get_random_user = sync_to_async(
        lambda: GameUser.objects.exclude(login_code=login_code).order_by("?").first()
    )
    get_random_game = sync_to_async(
        lambda: SentencePack.objects.select_related("author").order_by("?").first()
    )
    random_user = await get_random_user()
    random_game = await get_random_game()
    if not random_user:
        return Response(
            {"error": "No available players to match."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(
        {
            "message": "Player matched successfully.",
            "matched_user": {
                "id": random_user.id,
                "nickname": random_user.nickname,
                "username": random_user.username,
                "email": random_user.email,
            },
            "game": {
                "id": random_game.id,
                "name": random_game.name,
                "author": (
                    random_game.author.nickname if random_game.author else "Unknown"
                ),
            },
        },
        status=status.HTTP_200_OK,
    )
