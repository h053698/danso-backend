import random, string, aiohttp
from urllib.parse import urlencode
from asgiref.sync import sync_to_async

from django.http import HttpRequest, JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from adrf.decorators import api_view
from django.views.decorators.csrf import csrf_exempt

from danso import settings
from user.auth import login_code_to_user
from user.models import GameUser

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"


def generate_login_code():
    letter = random.choice(string.ascii_uppercase)
    numbers = "".join(random.choices(string.digits, k=6))
    return f"{letter}{numbers}"


async def exchange_code_for_token(code: str) -> dict:
    async with aiohttp.ClientSession() as session:
        data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        async with session.post(GOOGLE_TOKEN_URL, data=data) as response:
            if response.status == 200:
                token_data = await response.json()
                access_token = token_data.get("access_token")
                if not access_token:
                    raise Exception("Access token not found in response")
                user_data = await get_oauth_user_data(access_token)
                return user_data
            raise Exception(
                f"Failed to exchange code for token: {response.status} {response.reason}"
            )


async def get_oauth_user_data(access_token: str) -> dict:
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with session.get(GOOGLE_USERINFO_URL, headers=headers) as response:
            if response.status == 200:
                user_data = await response.json()
                return user_data
            raise Exception(
                f"Failed to fetch user data: {response.status} {response.reason}"
            )


@api_view(["GET"])
async def login_oauth_url(request: HttpRequest):
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "email profile",
        "access_type": "offline",
        "prompt": "consent",
    }

    return redirect(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@api_view(["GET"])
async def user_info(request: HttpRequest):
    login_code = request.headers.get("X-Login-Code", None)
    if not login_code:
        return JsonResponse({"error": "Login code not provided"}, status=400)

    user = await login_code_to_user(login_code)
    if isinstance(user, HttpResponse):
        return user

    user_data = {
        "id": user.id,
        "nickname": user.nickname,
        "username": user.username,
        "email": user.email,
    }
    return JsonResponse(user_data)


@api_view(["POST"])
async def user_logout(request: HttpRequest):
    login_code = request.headers.get("X-Login-Code", None)
    if not login_code:
        return JsonResponse({"error": "Login code not provided"}, status=400)

    user = await login_code_to_user(login_code)
    if isinstance(user, HttpResponse):
        return user

    update_user = sync_to_async(
        lambda: GameUser.objects.filter(id=user.id).update(login_code=None)
    )
    await update_user()
    return JsonResponse({"message": "Logout successful"})


def login_view_render(request: HttpRequest):
    login_code = request.GET.get("login_code", None)
    if not login_code:
        return render(request, "error_login.html")
    return render(request, "success_login.html", {"login_code": login_code})


@api_view(["GET"])
async def login_oauth_callback(request: HttpRequest):
    code = request.GET.get("code")
    if not code:
        return JsonResponse({"error": "Authorization code not provided"}, status=400)
    try:
        user_data = await exchange_code_for_token(code)
    except Exception as e:
        return JsonResponse({"error": "Google Oauth request failed"}, status=400)
    user_email = user_data.get("email", None)
    if not user_email:
        return JsonResponse({"error": "Google Oauth request failed"}, status=400)
    login_code = generate_login_code()
    user_filter = sync_to_async(lambda: list(GameUser.objects.filter(email=user_email)))
    users = await user_filter()
    if len(users) == 0:
        create_user = sync_to_async(
            lambda: GameUser.objects.create(
                nickname=user_data.get("name"),
                username=user_data.get("email").split("@")[0],
                email=user_email,
                login_code=login_code,
            )
        )
        user = await create_user()
    else:
        user = users[0]
        update_user = sync_to_async(
            lambda: GameUser.objects.filter(id=user.id).update(login_code=login_code)
        )
        await update_user()
        get_updated_user = sync_to_async(lambda: GameUser.objects.get(id=user.id))
        user = await get_updated_user()
    return redirect(f"/login/result?login_code={login_code}")


@csrf_exempt
async def profile_edit(request: HttpRequest):
    if request.method == "POST":
        login_code = request.POST.get("login_code")
        if not login_code:
            return render(
                request,
                "error_auth.html",
                {"error_message": "세션이 만료되었거나 잘못된 인증값입니다."},
            )

        try:
            user = await login_code_to_user(login_code)
        except Exception:
            return render(
                request,
                "error_auth.html",
                {"error_message": "세션이 만료되었거나 잘못된 인증값입니다."},
            )

        # 프로필 정보 업데이트 (이메일 제외)
        nickname = request.POST.get("nickname")
        username = request.POST.get("username")

        if nickname:
            user.nickname = nickname
        if username:
            user.username = username

        await sync_to_async(user.save)()

        return redirect(f"/profile/edit?login_code={login_code}&success=1")

    elif request.method == "GET":
        login_code = request.GET.get("login_code")
        if not login_code:
            return render(
                request,
                "error_auth.html",
                {"error_message": "세션이 만료되었거나 잘못된 인증값입니다."},
            )

        try:
            user = await login_code_to_user(login_code)
        except Exception:
            return render(
                request,
                "error_auth.html",
                {"error_message": "세션이 만료되었거나 잘못된 인증값입니다."},
            )

        return render(
            request,
            "profile_edit.html",
            {
                "user": user,
                "login_code": login_code,
                "success": request.GET.get("success"),
            },
        )
    else:
        return HttpResponse("허용되지 않은 접근입니다.", status=403)
