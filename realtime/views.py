from adrf.decorators import api_view
from asgiref.sync import sync_to_async
from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from sentence.models import SentencePack
from user.auth import login_code_to_user
from user.models import GameUser
from .manager import RealtimeRoomManager

room_manager = RealtimeRoomManager()


@api_view(["POST"])
async def match_player(request: HttpRequest):
    login_code = request.headers.get("X-Login-Code", None)
    if not login_code:
        return Response(
            {"error": "Login code is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    user = await login_code_to_user(login_code)
    get_random_game = sync_to_async(
        lambda: SentencePack.objects.select_related("author").order_by("?").first()
    )
    random_game = await get_random_game()

    match_result = room_manager.join_random_room(str(user.id))

    response_data = {
        "room_id": match_result["room_id"],
        "status": match_result["status"],
        "players": match_result["players"],
        "game": {
            "id": random_game.id,
            "name": random_game.name,
            "author": random_game.author.nickname if random_game.author else "Unknown",
        },
    }

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["POST"])
async def join_room(request: HttpRequest):
    login_code = request.headers.get("X-Login-Code", None)
    room_id = request.POST.get("room_id", None)

    if not login_code or not room_id:
        return Response(
            {"error": "Login code and room_id are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = await login_code_to_user(login_code)
    get_random_game = sync_to_async(
        lambda: SentencePack.objects.select_related("author").order_by("?").first()
    )
    random_game = await get_random_game()

    # 특정 방에 입장
    join_result = room_manager.join_specific_room(room_id, str(user.id))

    if not join_result:
        return Response(
            {"error": "방을 찾을 수 없거나 만료된 코드입니다"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    response_data = {
        "room_id": join_result["room_id"],
        "status": join_result["status"],
        "players": join_result["players"],
        "game": {
            "id": random_game.id,
            "name": random_game.name,
            "author": random_game.author.nickname if random_game.author else "Unknown",
        },
    }

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(["GET"])
async def check_match_status(request: HttpRequest):
    login_code = request.headers.get("X-Login-Code", None)
    room_id = request.GET.get("room_id", None)

    if not login_code or not room_id:
        return Response(
            {"error": "Login code and room_id are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = await login_code_to_user(login_code)
    room = room_manager.get_room(room_id)

    if not room:
        return Response({"error": "Room not found"}, status=status.HTTP_404_NOT_FOUND)

    is_matched = len(room["players"]) >= 2
    is_in_room = str(user.id) in room["players"]

    # 이미 게임이 선택되어 있는지 확인
    existing_game = room_manager.get_room_game(room_id)

    if is_matched and not existing_game:
        # 매칭되었고 아직 게임이 선택되지 않은 경우, 랜덤 게임 선택
        get_random_game = sync_to_async(
            lambda: SentencePack.objects.select_related("author").order_by("?").first()
        )
        random_game = await get_random_game()

        print(random_game.sentences)
        game_data = {
            "id": random_game.id,
            "name": random_game.name,
            "author": random_game.author.nickname if random_game.author else "Unknown",
            "sentences": [sentence.content for sentence in random_game.sentences.all()],
        }

        # 게임 데이터를 방 세션에 저장
        room_manager.set_room_game(room_id, game_data)
        existing_game = game_data

    response_data = {
        "room_id": room_id,
        "status": "matched" if is_matched else "waiting",
        "is_in_room": is_in_room,
        "players": room["players"],
        "player_count": len(room["players"]),
    }

    if is_matched and existing_game:
        response_data["game"] = existing_game

    return Response(response_data)


@api_view(["POST"])
async def in_game_heartbeat(request: HttpRequest, room_id: str):
    login_code = request.headers.get("X-Login-Code", None)
    now_text = request.POST.get("now_text", "")
    position = request.POST.get("position", 0)
    heart = request.POST.get("heart", 3)  # 기본값 3

    if not login_code or not room_id:
        return Response(
            {"error": "Login code and room_id are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = await login_code_to_user(login_code)
    room = room_manager.get_room(room_id)

    if not room:
        return Response({"error": "Room not found"}, status=status.HTTP_404_NOT_FOUND)

    if str(user.id) not in room["players"]:
        return Response(
            {"error": "User is not in the room"}, status=status.HTTP_403_FORBIDDEN
        )

    if room_manager.check_game_timeout(room_id):
        room_manager.add_event(room_id, str(user.id), "game_ended")
        room_manager.end_game(room_id)
        return Response({"event": "game_ended"}, status=status.HTTP_200_OK)

    # 유저의 게임 상태 업데이트
    room_manager.update_user_game_status(
        room_id, str(user.id), now_text, int(position), int(heart)
    )

    # 상대방 상태 가져오기
    opponent_status = room_manager.get_opponent_status(room_id, str(user.id))
    events = room_manager.get_and_clear_events(room_id, str(user.id))

    if events:
        opponent_status["event"] = events[0]

    if not opponent_status:
        return Response(
            {"error": "Game Session not found"}, status=status.HTTP_404_NOT_FOUND
        )

    if (
        opponent_status.get("event") == "timeout"
        and opponent_status["heart"] > 0
        and len(room["players"]) >= 2
    ):
        opponent_status["event"] = "reconnected"

    return Response(opponent_status, status=status.HTTP_200_OK)


@api_view(["POST"])
async def leave_room(request: HttpRequest, room_id: str):
    login_code = request.headers.get("X-Login-Code", None)
    if not login_code or not room_id:
        return Response(
            {"error": "Login code and room_id are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = await login_code_to_user(login_code)

    if room_manager.leave_room(room_id, str(user.id)):
        room_manager.add_event(room_id, str(user.id), "left")
        return Response({"status": "success"})

    return Response(
        {"error": "Failed to leave room"},
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["POST"])
async def missed_word(request: HttpRequest, room_id: str):
    login_code = request.headers.get("X-Login-Code", None)
    if not login_code or not room_id:
        return Response(
            {"error": "Login code and room_id are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = await login_code_to_user(login_code)

    # 하트 감소
    if room_manager.missed_word(room_id, str(user.id)):
        # 상대방에게 damaged 이벤트 전달
        room_manager.add_event(room_id, str(user.id), "damaged")
        return Response({"status": "success"})

    return Response(
        {"error": "Failed to process missed word"}, status=status.HTTP_400_BAD_REQUEST
    )
