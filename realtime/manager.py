import time
import uuid, random
from django.core.cache import cache


class RealtimeRoomManager:
    WAITING_ROOM_KEY = "waiting_rooms"

    @staticmethod
    def generate_room_code() -> str:
        while True:
            code = str(random.randint(100000, 999999))
            if not cache.get(f"room:{code}"):
                return str(code)

    def join_random_room(self, user_id: str):
        waiting_rooms = cache.get(self.WAITING_ROOM_KEY, [])

        # 먼저 유저가 이미 어떤 방에 있는지 확인
        for room_id in waiting_rooms:
            room = cache.get(f"room:{room_id}")
            if room and user_id in room["players"]:
                # 이미 방에 있다면 같은 상태를 반환
                if "player_status" not in room:
                    room["player_status"] = {}
                if user_id not in room["player_status"]:
                    room["player_status"][user_id] = {"heart": 5}
                    cache.set(f"room:{room_id}", room, timeout=3600)
                return {
                    "room_id": room_id,
                    "status": "matched" if len(room["players"]) >= 2 else "waiting",
                    "players": room["players"],
                }

        # 호스트인 방이 있는지 확인
        for room_id in waiting_rooms:
            room = cache.get(f"room:{room_id}")
            if room and len(room["players"]) == 1 and room["players"][0] == user_id:
                # 내가 호스트인 방이 있다면 그 방의 상태를 반환
                return {
                    "room_id": room_id,
                    "status": "waiting",
                    "players": room["players"],
                }

        # 대기 중인 방 중에서 매칭 가능한 방 찾기
        for i, room_id in enumerate(waiting_rooms):
            room = cache.get(f"room:{room_id}")
            if room and len(room["players"]) == 1 and user_id not in room["players"]:
                # 적합한 방을 찾았을 때
                waiting_rooms.pop(i)
                room["players"].append(user_id)
                cache.set(f"room:{room_id}", room, timeout=3600)
                cache.set(self.WAITING_ROOM_KEY, waiting_rooms)
                return {
                    "room_id": room_id,
                    "status": "matched",
                    "players": room["players"],
                }

        # 적합한 방을 찾지 못했고 호스트인 방도 없을 경우에만 새로운 방 생성
        room_id = self.generate_room_code()
        room_data = {"players": [user_id], "type": "waiting"}
        cache.set(f"room:{room_id}", room_data, timeout=600)
        waiting_rooms.append(room_id)
        cache.set(self.WAITING_ROOM_KEY, waiting_rooms)
        return {"room_id": room_id, "status": "waiting", "players": [user_id]}

    @staticmethod
    def leave_room(room_id: str, user_id: str):
        key = f"room:{room_id}"
        room = cache.get(key)
        if not room:
            return False

        if user_id in room["players"]:
            room["players"].remove(user_id)

            # 방에 아무도 없으면 방 삭제
            if not room["players"]:
                cache.delete(key)
                # 대기방 목록에서도 제거
                waiting_rooms = cache.get(RealtimeRoomManager.WAITING_ROOM_KEY, [])
                if room_id in waiting_rooms:
                    waiting_rooms.remove(room_id)
                    cache.set(RealtimeRoomManager.WAITING_ROOM_KEY, waiting_rooms)
            else:
                cache.set(key, room, timeout=3600)
            return True
        return False

    @staticmethod
    def join_specific_room(room_id: str, user_id: str):
        key = f"room:{room_id}"
        room = cache.get(key)

        if not room:
            room = {
                "players": [user_id],
                "type": "custom",
                "player_status": {user_id: {"heart": 5}},
            }
            cache.set(key, room, timeout=3600)
            return {"room_id": room_id, "status": "waiting", "players": [user_id]}

        if "player_status" not in room:
            room["player_status"] = {}
        room["player_status"][user_id] = {"heart": 5}
        room["players"].append(user_id)
        cache.set(key, room, timeout=3600)

        return {
            "room_id": room_id,
            "status": "matched" if len(room["players"]) >= 2 else "waiting",
            "players": room["players"],
        }

    @staticmethod
    def end_game(room_id: str):
        key = f"room:{room_id}"
        cache.delete(key)
        return {"room_id": room_id, "status": "ended"}

    @staticmethod
    def get_room(room_id: str):
        return cache.get(f"room:{room_id}")

    @staticmethod
    def set_room_game(room_id: str, game_data: dict):
        key = f"room:{room_id}"
        room = cache.get(key)
        if room:
            room["game"] = game_data
            cache.set(key, room, timeout=3600)
            return True
        return False

    @staticmethod
    def get_room_game(room_id: str):
        room = cache.get(f"room:{room_id}")
        return room.get("game") if room else None

    @staticmethod
    def update_user_game_status(
        room_id: str, user_id: str, now_text: str, position: int, heart: int
    ):
        key = f"room:{room_id}"
        room = cache.get(key)
        if not room:
            return False

        current_time = time.time()

        if "player_status" not in room:
            room["player_status"] = {}

        # 진행률 계산
        total_sentences = len(room["game"]["sentences"])
        completion_percentage = (position / total_sentences) * 100

        room["player_status"][user_id] = {
            "now_text": now_text,
            "position": position,
            "heart": heart,
            "completion_percentage": completion_percentage,
            "last_heartbeat": current_time,
        }

        cache.set(key, room, timeout=3600)
        return True

    @staticmethod
    def get_opponent_status(room_id: str, user_id: str):
        room = cache.get(f"room:{room_id}")
        if not room or "player_status" not in room:
            return None

        current_time = time.time()
        events = []

        opponent_id = None
        for player_id in room["players"]:
            if player_id != user_id:
                opponent_id = player_id
                break

        if not opponent_id:
            return None

        opponent_status = room["player_status"].get(opponent_id)
        if not opponent_status:
            return {"event": "timeout"}

        # 하트비트 체크 (5초)
        if current_time - opponent_status["last_heartbeat"] > 5:
            events.append("timeout")

        # 하트 변화 체크
        if opponent_status["heart"] <= 0:
            events.append("damaged")

        # 플레이어 수 체크
        if len(room["players"]) < 2:
            events.append("left")

        response = {
            "now_text": opponent_status["now_text"],
            "position": opponent_status["position"],
            "heart": opponent_status["heart"],
            "completion_percentage": opponent_status["completion_percentage"],
            "event": events[0] if events else "idle",  # 이벤트가 없으면 'idle' 반환
        }

        return response

    @staticmethod
    def add_event(room_id: str, user_id: str, event_type: str):
        key = f"room:{room_id}"
        room = cache.get(key)
        if not room:
            return False

        if "events" not in room:
            room["events"] = {}

        # 각 유저별 이벤트 저장
        for player_id in room["players"]:
            if player_id != user_id:  # 이벤트를 상대방에게만 전달
                if player_id not in room["events"]:
                    room["events"][player_id] = []
                room["events"][player_id].append(event_type)

        cache.set(key, room, timeout=3600)
        return True

    @staticmethod
    def get_and_clear_events(room_id: str, user_id: str):
        key = f"room:{room_id}"
        room = cache.get(key)
        if not room or "events" not in room:
            return []

        events = room["events"].get(user_id, [])
        if user_id in room["events"]:
            room["events"][user_id] = []  # 이벤트 클리어
            cache.set(key, room, timeout=3600)
        return events

    @staticmethod
    def missed_word(room_id: str, user_id: str):
        key = f"room:{room_id}"
        room = cache.get(key)
        if not room or "player_status" not in room:
            return False

        player_status = room["player_status"].get(user_id)
        if player_status:
            player_status["heart"] = max(0, player_status["heart"] - 1)
            cache.set(key, room, timeout=3600)
            return True
        return False

    @staticmethod
    def check_game_timeout(room_id: str):
        room = cache.get(f"room:{room_id}")
        if not room or "player_status" not in room:
            return False

        current_time = time.time()
        for player_id, status in room["player_status"].items():
            if current_time - status["last_heartbeat"] > 20:  # 20초 타임아웃
                return True
        return False
