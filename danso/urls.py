from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from danso.views import api_docs, api_root
from sentence.views import (
    get_sentence_packs,
    get_sentence_by_id,
    get_sentence_game,
    search_sentence_pack,
    get_sentence_packs_random,
    update_sentence_game_point,
    interact_like_sentence_pack,
    add_sentence_pack_dashboard,
    dashboard_sentence_pack_list,
    dashboard_sentence_pack_edit,
    dashboard_sentence_pack_delete,
    serve_sentence_pack_image,
)
from user.views import (
    login_oauth_url,
    login_oauth_callback,
    login_view_render,
    user_info,
    user_logout,
)
from realtime.views import (
    match_player,
    check_match_status,
    in_game_heartbeat,
    join_room,
    missed_word,
    leave_room,
)

urlpatterns = [
    path("", api_docs, name="api-docs"),  # HTML 문서
    path("api/", api_root, name="api-root"),  # JSON API
    path("admin/", admin.site.urls),
    path("sentences/", get_sentence_packs, name="sentences"),
    path(
        "sentences/<int:sentence_pack_id>/set-score",
        update_sentence_game_point,
        name="update-sentence-game-point",
    ),
    path("sentences/random", get_sentence_packs_random, name="random-sentences"),
    path("sentences/search", search_sentence_pack, name="search-sentence-pack"),
    path("sentences/<int:sentence_id>", get_sentence_by_id, name="sentence-detail"),
    path("sentences/<int:sentence_id>/game", get_sentence_game, name="sentence-game"),
    path(
        "sentences/{int:sentence_pack_id}/interact-like",
        interact_like_sentence_pack,
        name="sentence-interact-like",
    ),
    path("login/oauth/", login_oauth_url, name="login-oauth-url"),
    path("login/callback", login_oauth_callback, name="login-oauth-callback"),
    path("login/result", login_view_render, name="login-result"),
    path("user/me", user_info, name="login-view"),
    path("user/logout", user_logout, name="user-logout"),
    path("realtime/match/player", match_player, name="match-player"),
    path("realtime/match/status", check_match_status, name="match-status"),
    path("realtime/match/join", join_room, name="join-match"),
    path(
        "realtime/game/<str:room_id>/heartbeat",
        in_game_heartbeat,
        name="realtime-game-room",
    ),
    path("realtime/game/<str:room_id>/missed", missed_word, name="realtime-game-join"),
    path("realtime/game/<str:room_id>/leave", leave_room, name="realtime-game-leave"),
    path(
        "dashboard/add-sentence-pack",
        add_sentence_pack_dashboard,
        name="add_sentence_pack_dashboard",
    ),
    path(
        "dashboard/", dashboard_sentence_pack_list, name="dashboard_sentence_pack_list"
    ),
    path(
        "dashboard/edit/<int:pk>/",
        dashboard_sentence_pack_edit,
        name="dashboard_sentence_pack_edit",
    ),
    path(
        "dashboard/delete/<int:pk>/",
        dashboard_sentence_pack_delete,
        name="dashboard_sentence_pack_delete",
    ),
    path(
        "image/<str:image_id>",
        serve_sentence_pack_image,
        name="serve_sentence_pack_image",
    ),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
