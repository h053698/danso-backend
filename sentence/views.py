from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def sentences(request):
    sentences_data = [
        {"id": 1, "text": "애국가"},
        {"id": 2, "text": "YENA(최예나) '네모네모 (NEMONEMO)' 가사"},
    ]

    return Response(sentences_data, status=status.HTTP_200_OK)


@api_view(["GET"])
def sentence_detail(request, sentence_id: int):
    sentences_content = {
        1: [
            "동해물과 백두산이 마르고 닳도록",
            "하느님이 보우하사 우리나라 만세",
            "무궁화 삼천리 화려강산",
            "대한사람 대한으로 길이 보전하세",
        ],
        2: [
            "네모난 세상 속에 갇혀있던 나",
            "네모난 틀에 맞춰 살았었나 봐",
            "네모난 생각들이 날 옭아매도",
            "이제는 달라질 거야",
        ],
    }

    if sentence_id not in sentences_content:
        return Response(
            {"error": "찾을 수 없는 문장 그룹입니다."}, status=status.HTTP_404_NOT_FOUND
        )

    return Response(
        {"id": sentence_id, "sentences": sentences_content[sentence_id]},
        status=status.HTTP_200_OK,
    )
