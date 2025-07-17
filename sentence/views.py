from typing import Callable, Coroutine, Any

from asgiref.sync import sync_to_async
from django.conf import settings
from django.http import HttpRequest, HttpResponse, Http404
from rest_framework import status
from adrf.decorators import api_view
from rest_framework.response import Response

from danso.settings import R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL, R2_BUCKET_NAME
from sentence.models import SentencePack, SentencePackLike
from user.auth import login_code_to_user
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import mimetypes
import boto3
import uuid
import os


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
            "original_author": sentence.original_author,
            "total_likes": await sentence.get_total_likes(),
            # "is_liked": SentencePackLike.objects.filter(user=request.user, pack=sentence).exists()
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
            "original_author": sentence.original_author,
            "total_likes": await sentence.get_total_likes(),
            # "is_liked": SentencePackLike.objects.filter(user=request.user, pack=sentence).exists()
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
        get_keyword_filter: Callable[..., Coroutine[Any, Any, list[SentencePack]]] = (
            sync_to_async(
                lambda: list(
                    SentencePack.objects.select_related("author").filter(
                        name__icontains=keyword
                    )
                )
            )
        )
        sentences = await get_keyword_filter()
    elif level:
        get_level_filter: Callable[..., Coroutine[Any, Any, list[SentencePack]]] = (
            sync_to_async(
                lambda: list(
                    SentencePack.objects.select_related("author").filter(level=level)
                )
            )
        )
        sentences = await get_level_filter()
    elif author:
        get_author_filter: Callable[..., Coroutine[Any, Any, list[SentencePack]]] = (
            sync_to_async(
                lambda: list(
                    SentencePack.objects.select_related("author").filter(
                        author__nickname__icontains=author
                    )
                )
            )
        )
        sentences: list[SentencePack] = await get_author_filter()
    return Response(
        [
            {
                "id": sentence.id,
                "name": sentence.name,
                "author": sentence.author.nickname if sentence.author else "Unknown",
                "original_author": sentence.original_author,
                "level": sentence.level,
                "total_likes": await sentence.get_total_likes(),
                # "is_liked": SentencePackLike.objects.filter(user=request.user, pack=sentence).exists()
            }
            for sentence in sentences
        ],
        status=status.HTTP_200_OK,
    )


async def get_leaderboard_data(sentence_pack: SentencePack):
    get_all_leaderboards = sync_to_async(
        lambda: list(
            sentence_pack.leaderboards.all().select_related("player").order_by("-score")
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
            "original_author": sentence_pack.original_author,
            "sentences": sentence_pack.sentences.split("\r\n"),
            "total_likes": await sentence_pack.get_total_likes(),
            # "is_liked": SentencePackLike.objects.filter(user=request.user, pack=sentence_pack).exists()
        },
        status=status.HTTP_200_OK,
    )


async def get_user_rank_data(sentence_pack: SentencePack, user):
    get_leaderboard = sync_to_async(
        lambda: sentence_pack.leaderboards.filter(player=user).first()
    )

    get_all_ranks = sync_to_async(
        lambda: list(
            sentence_pack.leaderboards.order_by("-score").values_list(
                "score", flat=True
            )
        )
    )
    get_top5_players = sync_to_async(
        lambda: list(
            sentence_pack.leaderboards.order_by("-score").values_list(
                "player_id", flat=True
            )[:5]
        )
    )

    user_leaderboard = await get_leaderboard()
    all_scores = await get_all_ranks()
    top5_player_ids = await get_top5_players()

    if user_leaderboard:
        user_score = user_leaderboard.score
        user_rank = all_scores.index(user_score) + 1
    else:
        user_score = 0
        user_rank = len(all_scores) + 1

    get_nearby_users = sync_to_async(
        lambda: list(
            sentence_pack.leaderboards.select_related("player")
            .order_by("-score")
            .filter(score__gte=user_score)[:1]
            .union(
                sentence_pack.leaderboards.select_related("player")
                .order_by("-score")
                .filter(score__lte=user_score)[:1]
            )
        )
    )

    nearby_users = await get_nearby_users()

    def is_in_top5(nearby_user):
        return getattr(nearby_user, "player_id", None) in top5_player_ids

    nearby_user_1 = {"player": "없음", "score": 0, "rank": user_rank - 1}

    nearby_user_2 = {"player": "없음", "score": 0, "rank": user_rank + 1}

    if len(nearby_users) > 0 and nearby_users[0] and not is_in_top5(nearby_users[0]):
        if getattr(nearby_users[0], "player", None):
            nearby_user_1 = {
                "player": nearby_users[0].player.nickname or "없음",
                "score": nearby_users[0].score,
                "rank": user_rank - 1,
            }
    if len(nearby_users) > 1 and nearby_users[1] and not is_in_top5(nearby_users[1]):
        if getattr(nearby_users[1], "player", None):
            nearby_user_2 = {
                "player": nearby_users[1].player.nickname or "없음",
                "score": nearby_users[1].score,
                "rank": user_rank + 1,
            }

    return {
        "my_score": user_score,
        "my_rank": user_rank,
        "my_nearest_rank_user_1": nearby_user_1,
        "my_nearest_rank_user_2": nearby_user_2,
    }


@api_view(["POST"])
async def update_sentence_game_point(request: HttpRequest, sentence_pack_id: int):
    if not sentence_pack_id:
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
            lambda: SentencePack.objects.select_related("author").get(
                id=sentence_pack_id
            )
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

    new_score = int(score)
    if created or leaderboard.score < new_score:
        leaderboard.score = new_score
        await sync_to_async(leaderboard.save)()
        message = "최고 점수가 업데이트되었습니다."
    else:
        message = "기존 최고 점수보다 낮아 업데이트되지 않았습니다."

    return Response({"message": message}, status=status.HTTP_200_OK)


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
            "original_author": sentence_pack.original_author,
            "leaderboard": [
                {
                    "player": (
                        leaderboard.player.nickname
                        if leaderboard.player
                        else "알 수 없음"
                    ),
                    "score": leaderboard.score,
                }
                for leaderboard in leaderboards
            ],
            **rank_data,
            "total_likes": await sentence_pack.get_total_likes(),
            "is_liked": await sync_to_async(
                lambda: SentencePackLike.objects.filter(
                    user=user, pack=sentence_pack
                ).exists()
            )(),
            "image_url": (
                f"https://danso-cdn.thnos.app/sentence-image/{sentence_pack.image_id}"
                if sentence_pack.image_id
                else None
            ),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
async def interact_like_sentence_pack(request: HttpRequest, sentence_id: int):
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
            lambda: SentencePack.objects.get(id=sentence_id)
        )
        sentence_pack = await get_sentence_pack()
    except SentencePack.DoesNotExist:
        return Response(
            {"error": "찾을 수 없는 문장 그룹입니다."}, status=status.HTTP_404_NOT_FOUND
        )

    like, created = await sync_to_async(
        lambda: SentencePackLike.objects.get_or_create(user=user, pack=sentence_pack)
    )()

    if created:
        message = "문장 그룹에 좋아요를 추가했습니다."
    else:
        await sync_to_async(like.delete)()
        message = "문장 그룹의 좋아요를 취소했습니다."

    return Response({"message": message}, status=status.HTTP_200_OK)


def upload_to_r2(file_obj, filename):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        endpoint_url=R2_ENDPOINT_URL,
    )
    s3.upload_fileobj(
        file_obj,
        R2_BUCKET_NAME,
        filename,
        ExtraArgs={"ACL": "public-read", "ContentType": file_obj.content_type},
    )
    return f"https://danso-cdn.thnos.app/{filename}"


@csrf_exempt
async def add_sentence_pack_dashboard(request):
    if request.method == "POST":
        login_code = request.POST.get("login_code")
        if not login_code:
            return HttpResponse("로그인 코드가 필요합니다.", status=400)
        user = await login_code_to_user(login_code)
        name = request.POST.get("name")
        original_author = request.POST.get("original_author")
        sentences = request.POST.get("sentences")
        level = request.POST.get("level")
        image_file = request.FILES.get("image_file")
        image_url = None
        if image_file:
            ext = os.path.splitext(image_file.name)[1]
            rand = uuid.uuid4().hex[:8]
            filename = f"sentence_pack_images/{rand}{ext}"
            image_url = upload_to_r2(image_file, filename)
        await sync_to_async(SentencePack.objects.create)(
            name=name,
            original_author=original_author,
            author=user,
            sentences=sentences,
            level=level,
            image_url=image_url,
        )
        return redirect(f"/dashboard/add-sentence-pack?success=1&login_code={login_code}")
    elif request.method == "GET":
        login_code = request.GET.get("login_code")
        if not login_code:
            return render(request, "error_auth.html", {"error_message": "세션이 만료되었거나 잘못된 인증값입니다"})
        try:
            user = await login_code_to_user(login_code)
        except Exception:
            return render(request, "error_auth.html", {"error_message": "세션이 만료되었거나 잘못된 인증값입니다"})
        return render(
            request,
            "add_sentence_pack_dashboard.html",
            {"LEVEL_CHOICES": SentencePack.LEVEL_CHOICES, "login_user_nickname": user.nickname, "login_code": login_code, "success": request.GET.get("success")},
        )
    else:
        return HttpResponse("허용되지 않은 접근입니다.", status=403)


@csrf_exempt
async def dashboard_sentence_pack_list(request):
    login_code = request.GET.get("login_code")
    if not login_code:
        return render(request, "error_auth.html", {"error_message": "세션이 만료되었거나 잘못된 인증값입니다"})
    try:
        user = await login_code_to_user(login_code)
    except Exception:
        return render(request, "error_auth.html", {"error_message": "세션이 만료되었거나 잘못된 인증값입니다"})
    packs = await sync_to_async(lambda: list(SentencePack.objects.filter(author=user).select_related("author")))()
    # 각 pack의 total_likes 계산
    packs_with_likes = []
    for pack in packs:
        total_likes = await pack.get_total_likes()
        packs_with_likes.append({"pack": pack, "total_likes": total_likes})
    return render(request, "dashboard_sentence_pack_list.html", {"packs": packs_with_likes, "login_user_nickname": user.nickname, "login_code": login_code})


@csrf_exempt
async def dashboard_sentence_pack_edit(request, pk):
    if request.method == "POST":
        try:
            pack = await sync_to_async(SentencePack.objects.get)(pk=pk)
        except SentencePack.DoesNotExist:
            return redirect("dashboard_sentence_pack_list")
        login_code = request.POST.get("login_code")
        if not login_code:
            return render(request, "error_auth.html", {"error_message": "세션이 만료되었거나 잘못된 인증값입니다"})
        user = await login_code_to_user(login_code)
        pack.name = request.POST.get("name")
        pack.original_author = request.POST.get("original_author")
        pack.sentences = request.POST.get("sentences")
        pack.level = request.POST.get("level")
        image_file = request.FILES.get("image_file")
        image_url = None
        if image_file:
            ext = os.path.splitext(image_file.name)[1]
            rand = uuid.uuid4().hex[:8]
            filename = f"sentence_pack_images/{rand}{ext}"
            image_url = upload_to_r2(image_file, filename)
        pack.image_url = image_url
        pack.author = user
        await sync_to_async(pack.save)()
        return redirect(f"/dashboard/edit/{pk}/?login_code={login_code}&success=1")
    elif request.method == "GET":
        login_code = request.GET.get("login_code")
        if not login_code:
            return render(request, "error_auth.html", {"error_message": "세션이 만료되었거나 잘못된 인증값입니다"})
        try:
            user = await login_code_to_user(login_code)
        except Exception:
            return render(request, "error_auth.html", {"error_message": "세션이 만료되었거나 잘못된 인증값입니다"})
        try:
            pack = await sync_to_async(SentencePack.objects.get)(pk=pk)
        except SentencePack.DoesNotExist:
            return redirect("dashboard_sentence_pack_list")
        return render(
            request,
            "dashboard_sentence_pack_edit.html",
            {"pack": pack, "LEVEL_CHOICES": SentencePack.LEVEL_CHOICES, "login_user_nickname": user.nickname, "login_code": login_code, "success": request.GET.get("success")},
        )
    else:
        return HttpResponse("허용되지 않은 접근입니다.", status=403)


@require_http_methods(["POST"])
async def dashboard_sentence_pack_delete(request, pk):
    login_code = request.GET.get("login_code")
    if not login_code:
        return render(request, "error_auth.html", {"error_message": "세션이 만료되었거나 잘못된 인증값입니다"})
    try:
        pack = await sync_to_async(SentencePack.objects.get)(pk=pk)
        await sync_to_async(pack.delete)()
    except SentencePack.DoesNotExist:
        pass
    return redirect(f"/dashboard/?login_code={login_code}")


def serve_sentence_pack_image(request, image_id):
    try:
        pack = SentencePack.objects.get(image_id=image_id)
        if not pack.image_file:
            raise Http404()
        image_path = pack.image_file.path
        with open(image_path, "rb") as f:
            image_data = f.read()
        content_type, _ = mimetypes.guess_type(image_path)
        return HttpResponse(image_data, content_type=content_type)
    except (SentencePack.DoesNotExist, ValueError, FileNotFoundError):
        raise Http404()
