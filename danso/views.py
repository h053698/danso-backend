from django.shortcuts import render
from django.urls import get_resolver
from rest_framework.decorators import api_view
from rest_framework.response import Response


def get_all_urls(url_patterns, base='', urls=None):
    if urls is None:
        urls = {}

    for pattern in url_patterns:
        if hasattr(pattern, 'url_patterns'):
            # URL pattern이 include된 경우
            get_all_urls(pattern.url_patterns, base + str(pattern.pattern), urls)
        else:
            # 단일 URL pattern인 경우
            full_path = base + str(pattern.pattern)
            # admin 페이지 제외
            if not full_path.startswith('admin/'):
                view = pattern.callback
                # HTTP 메소드 가져오기
                if hasattr(view, 'cls'):
                    methods = [m.upper() for m in view.cls.http_method_names if m != 'options']
                elif hasattr(view, 'actions'):
                    methods = [m.upper() for m in view.actions.keys()]
                else:
                    methods = ['GET']  # 기본값

                for method in methods:
                    key = f"{method} {full_path}"
                    if hasattr(view, '__doc__') and view.__doc__:
                        urls[key] = view.__doc__.strip()
                    else:
                        urls[key] = "설명이 없습니다."

    return urls


def api_docs(request):
    """API 문서 페이지를 렌더링합니다."""
    resolver = get_resolver()
    all_urls = get_all_urls(resolver.url_patterns)

    # URL들을 그룹화
    grouped_urls = {
        "sentences": {},
        "user": {},
        "realtime": {},
        "other": {},
    }

    for url, desc in all_urls.items():
        if url.startswith(("GET /sentences", "POST /sentences")):
            grouped_urls["sentences"][url] = desc
        elif url.startswith(("GET /user", "POST /user", "GET /login")):
            grouped_urls["user"][url] = desc
        elif url.startswith(("GET /realtime", "POST /realtime")):
            grouped_urls["realtime"][url] = desc
        else:
            grouped_urls["other"][url] = desc

    return render(request, "api_docs.html", {"api_docs": grouped_urls})


@api_view(["GET"])
def api_root(request):
    """API 루트 페이지를 반환합니다."""
    resolver = get_resolver()
    all_urls = get_all_urls(resolver.url_patterns)

    return Response({
        "version": "1.0.0",
        "title": "Danso API",
        "description": "단소 게임 서버 API",
        "endpoints": all_urls
    })