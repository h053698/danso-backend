from asgiref.sync import sync_to_async
from django.http import HttpRequest
from rest_framework import status
from adrf.decorators import api_view
from rest_framework.response import Response
from sentence.models import SentencePack
from user.auth import login_code_to_user


@api_view(["GET"])
async def get_sentence_packs(request: HttpRequest):
    get_sentences_all = sync_to_async(
        lambda: list(SentencePack.objects.select_related("author").all())
    )
    sentences = await get_sentences_all()
    sentences_data = [
        {
            "id": sentence.id,
            "name": sentence.name,
            "author": sentence.author.nickname if sentence.author else "Unknown",
        }
        for sentence in sentences
    ]
    return Response(sentences_data, status=status.HTTP_200_OK)


@api_view(["GET"])
async def get_sentence_packs_random(request: HttpRequest):
    get_sentences_random = sync_to_async(
        lambda: list(SentencePack.objects.select_related("author").order_by("?")[:10])
    )
    sentences = await get_sentences_random()
    sentences_data = [
        {
            "id": sentence.id,
            "name": sentence.name,
            "author": sentence.author.nickname if sentence.author else "Unknown",
        }
        for sentence in sentences
    ]
    return Response(sentences_data, status=status.HTTP_200_OK)


@api_view(["GET"])
async def search_sentence_pack(request: HttpRequest):
    keyword = request.GET.get("keyword", None)
    level = request.GET.get("level", None)
    author = request.GET.get("author", None)
    if not keyword and not level and not author:
        return Response(
            {"error": "검색어, 레벨 또는 저자를 제공해야 합니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if keyword:
        get_keyword_filter = sync_to_async(
            lambda: SentencePack.objects.filter(name__icontains=keyword)
        )
        sentences = await get_keyword_filter()
    elif level:
        get_level_filter = sync_to_async(
            lambda: SentencePack.objects.filter(level=level)
        )
        sentences = await get_level_filter()
    elif author:
        get_author_filter = sync_to_async(
            lambda: SentencePack.objects.filter(author__nickname__icontains=author)
        )
        sentences = await get_author_filter()
    return Response(
        [
            {
                "id": sentence.id,
                "name": sentence.name,
                "author": sentence.author.nickname if sentence.author else "Unknown",
            }
            for sentence in sentences
        ],
        status=status.HTTP_200_OK,
    )


async def get_leaderboard_data(sentence_pack: SentencePack):
    get_all_leaderboards = sync_to_async(
        lambda: list(
            sentence_pack.leaderboards.all()
            .select_related("player")
            .order_by("-total_score")
        )
    )
    all_leaderboards = await get_all_leaderboards()
    top_5 = list(all_leaderboards[:5])

    return top_5


@api_view(["GET"])
async def get_sentence_game(request: HttpRequest, sentence_id: int):
    if not sentence_id:
        return Response(
            {"error": "문장 그룹 ID가 제공되지 않았습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        get_sentence_pack = sync_to_async(
            lambda: SentencePack.objects.select_related("author").get(id=sentence_id)
        )
        sentence_pack = await get_sentence_pack()
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


async def get_user_rank_data(sentence_pack: SentencePack, user):
    get_leaderboard = sync_to_async(
        lambda: sentence_pack.leaderboards.filter(player=user).first()
    )

    get_all_ranks = sync_to_async(
        lambda: list(
            sentence_pack.leaderboards.order_by("-total_score").values_list(
                "total_score", flat=True
            )
        )
    )

    user_leaderboard = await get_leaderboard()
    all_scores = await get_all_ranks()

    if user_leaderboard:
        user_score = user_leaderboard.total_score
        user_rank = all_scores.index(user_score) + 1
    else:
        user_score = 0
        user_rank = len(all_scores) + 1

    get_nearby_users = sync_to_async(
        lambda: list(
            sentence_pack.leaderboards.select_related("player")
            .order_by("-total_score")
            .filter(total_score__gte=user_score)[:1]
            .union(
                sentence_pack.leaderboards.select_related("player")
                .order_by("-total_score")
                .filter(total_score__lte=user_score)[:1]
            )
        )
    )

    nearby_users = await get_nearby_users()

    nearby_user_1 = {"player": "없음", "score": 0, "rank": user_rank - 1}

    nearby_user_2 = {"player": "없음", "score": 0, "rank": user_rank + 1}

    if len(nearby_users) > 0:
        if nearby_users[0].total_score >= user_score:
            nearby_user_1 = {
                "player": (
                    nearby_users[0].player.nickname
                    if nearby_users[0].player
                    else "알 수 없음"
                ),
                "score": nearby_users[0].total_score,
                "rank": user_rank - 1,
            }
        if len(nearby_users) > 1:
            nearby_user_2 = {
                "player": (
                    nearby_users[1].player.nickname
                    if nearby_users[1].player
                    else "알 수 없음"
                ),
                "score": nearby_users[1].total_score,
                "rank": user_rank + 1,
            }

    return {
        "my_score": user_score,
        "my_rank": user_rank,
        "my_nearest_rank_user_1": nearby_user_1,
        "my_nearest_rank_user_2": nearby_user_2,
    }


@api_view(["POST"])
async def update_sentence_game_point(request: HttpRequest, sentence_id: int):
    if not sentence_id:
        return Response(
            {"error": "문장 그룹 ID가 제공되지 않았습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    login_code = request.headers.get("X-Login-Code", None)
    if not login_code:
        return Response(
            {"error": "로그인 코드가 제공되지 않았습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user = await login_code_to_user(login_code)

    try:
        get_sentence_pack = sync_to_async(
            lambda: SentencePack.objects.select_related("author").get(id=sentence_id)
        )
        sentence_pack = await get_sentence_pack()
    except SentencePack.DoesNotExist:
        return Response(
            {"error": "찾을 수 없는 문장 그룹입니다."}, status=status.HTTP_404_NOT_FOUND
        )

    score = request.POST.get("score", None)
    if score is None:
        return Response(
            {"error": "점수가 제공되지 않았습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    leaderboard, created = await sync_to_async(
        lambda: sentence_pack.leaderboards.get_or_create(player=user)
    )()

    leaderboard.total_score += score
    await sync_to_async(leaderboard.save)()

    return Response(
        {"message": "점수가 업데이트되었습니다."}, status=status.HTTP_200_OK
    )


@api_view(["GET"])
async def get_sentence_by_id(request: HttpRequest, sentence_id: int):
    if not sentence_id:
        return Response(
            {"error": "문장 그룹 ID가 제공되지 않았습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    login_code = request.headers.get("X-Login-Code", None)
    if not login_code:
        return Response(
            {"error": "로그인 코드가 제공되지 않았습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user = await login_code_to_user(login_code)

    try:
        get_sentence_pack = sync_to_async(
            lambda: SentencePack.objects.select_related("author").get(id=sentence_id)
        )
        sentence_pack = await get_sentence_pack()
    except SentencePack.DoesNotExist:
        return Response(
            {"error": "찾을 수 없는 문장 그룹입니다."}, status=status.HTTP_404_NOT_FOUND
        )

    leaderboards = await get_leaderboard_data(sentence_pack)
    rank_data = await get_user_rank_data(sentence_pack, user)

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
            **rank_data,
        },
        status=status.HTTP_200_OK,
    )
