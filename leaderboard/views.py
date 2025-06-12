from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def leaderboard_view(request):
    leaderboard_data = [
        {"username": "user1", "score": 100},
        {"username": "user2", "score": 90},
        {"username": "user3", "score": 80},
    ]

    return Response(leaderboard_data, status=status.HTTP_200_OK)
