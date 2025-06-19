from django.shortcuts import render
from django.urls import get_resolver
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.shortcuts import render

API_DOCUMENTATION = {
    "sentences": {
        "GET /sentences/": "문장 팩 목록을 가져옵니다.",
        "GET /sentences/random": "랜덤 문장 팩을 가져옵니다.",
        "GET /sentences/search": "문장 팩을 검색합니다.",
        "GET /sentences/<id>": "특정 문장 팩의 상세 정보를 가져옵니다.",
        "GET /sentences/<id>/game": "특정 문장 팩의 게임 정보를 가져옵니다.",
        "POST /sentences/<id>/set-score": "문장 팩의 점수를 설정합니다.",
    },
    "user": {
        "GET /user/me": "현재 로그인한 사용자 정보를 가져옵니다.",
        "GET /user/logout": "로그아웃합니다.",
        "GET /login/oauth/": "OAuth 로그인 URL을 가져옵니다.",
        "GET /login/callback": "OAuth 콜백을 처리합니다.",
        "GET /login/result": "로그인 결과를 렌더링합니다.",
    },
    "realtime": {
        "POST /realtime/match/player": "랜덤 매칭을 시작합니다.",
        "GET /realtime/match/status": "매칭 상태를 확인합니다.",
        "POST /realtime/match/join": "특정 방에 입장합니다.",
        "POST /realtime/game/<room_id>/heartbeat": {
            "description": "게임 진행 상태를 업데이트하고 상대방 정보를 받습니다.",
            "request": {
                "now_text": "현재 입력 중인 텍스트",
                "position": "현재 문장 위치 (숫자)",
                "heart": "현재 생명력",
            },
            "response": {
                "now_text": "상대방이 입력 중인 텍스트",
                "position": "상대방의 현재 문장 위치",
                "heart": "상대방의 생명력",
                "completion_percentage": "상대방의 진행률",
                "event": "게임 이벤트 (damaged/timeout/reconnected/game_ended/left)",
            },
        },
        "POST /realtime/game/<room_id>/missed": "단어를 틀렸을 때 호출합니다.",
    },
}


def api_docs(request):
    return render(request, "api_docs.html", {"api_docs": API_DOCUMENTATION})


@api_view(["GET"])
def api_root(request):
    """API 루트 페이지를 반환합니다."""
    return Response(
        {
            "version": "1.0.0",
            "title": "Danso API",
            "description": "단소 게임 서버 API",
            "endpoints": API_DOCUMENTATION,
        }
    )


def api_docs(request):
    """API 문서 페이지를 렌더링합니다."""
    return render(request, "api_docs.html", {"api_docs": API_DOCUMENTATION})
