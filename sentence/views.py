from rest_framework import status
from adrf.decorators import api_view
from rest_framework.response import Response
from sentence.models import SentencePack
from user.models import GameUser


@api_view(["GET"])
async def get_sentences(request):
    sentences = SentencePack.objects.all()
    sentences_data = [
        {
            "id": sentence.id,
            "name": sentence.name,
            "author": sentence.author.nickname if sentence.author else "Unknown",
        }
        for sentence in sentences
    ]
    return Response(sentences_data, status=status.HTTP_200_OK)


async def get_leaderboard_data(sentence_pack: SentencePack):
    all_leaderboards = sentence_pack.leaderboards.all().order_by("-total_score")

    top_5 = list(all_leaderboards[:5])

    return top_5


@api_view(["GET"])
async def get_sentence_game(request, sentence_id: int):
    if not sentence_id:
        return Response(
            {"error": "문장 그룹 ID가 제공되지 않았습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        sentence_pack = SentencePack.objects.get(id=sentence_id)
    except SentencePack.DoesNotExist:
        return Response(
            {"error": "찾을 수 없는 문장 그룹입니다."}, status=status.HTTP_404_NOT_FOUND
        )

    return Response(
        {
            "id": sentence_pack.id,
            "name": sentence_pack.name,
            "author": (
                sentence_pack.author.nickname if sentence_pack.author else "알 수 없음"
            ),
            "sentences": sentence_pack.sentences.split("\r\n"),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
async def get_sentence_by_id(request, sentence_id: int):
    if not sentence_id:
        return Response(
            {"error": "문장 그룹 ID가 제공되지 않았습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        sentence_pack = SentencePack.objects.get(id=sentence_id)
    except SentencePack.DoesNotExist:
        return Response(
            {"error": "찾을 수 없는 문장 그룹입니다."}, status=status.HTTP_404_NOT_FOUND
        )

    leaderboards = await get_leaderboard_data(sentence_pack)

    return Response(
        {
            "id": sentence_pack.id,
            "name": sentence_pack.name,
            "author": (
                sentence_pack.author.nickname if sentence_pack.author else "알 수 없음"
            ),
            "leaderboard": [
                {
                    "player": (
                        leaderboard.player.nickname
                        if leaderboard.player
                        else "알 수 없음"
                    ),
                    "score": leaderboard.total_score,
                }
                for leaderboard in leaderboards
            ],
            "my_score": 0,
            "my_rank": 501,
            "my_nearest_rank_user_1": {
                "player": "테스트 유저1",
                "score": 0,
                "rank": 500,
            },
            "my_nearest_rank_user_2": {
                "player": "테스트 유저2",
                "score": 0,
                "rank": 502,
            },
        },
        status=status.HTTP_200_OK,
    )
