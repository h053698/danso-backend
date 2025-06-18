"""
URL configuration for danso project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from sentence.views import get_sentence_packs, get_sentence_by_id, get_sentence_game, search_sentence_pack, get_sentence_packs_random
from user.views import (
    login_oauth_url,
    login_oauth_callback,
    login_view_render,
    user_info,
    user_logout,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sentences/", get_sentence_packs, name="sentences"),
    path("sentences/random/", get_sentence_packs_random, name="random-sentences"),
    path("sentences/search/", search_sentence_pack, name="search-sentence-pack"),
    path("sentences/<int:sentence_id>/", get_sentence_by_id, name="sentence-detail"),
    path("sentences/<int:sentence_id>/game/", get_sentence_game, name="sentence-game"),
    path("login/oauth/", login_oauth_url, name="login-oauth-url"),
    path("login/callback", login_oauth_callback, name="login-oauth-callback"),
    path("login/result", login_view_render, name="login-result"),
    path("user/me", user_info, name="login-view"),
    path("user/logout", user_logout, name="user-logout"),
]
