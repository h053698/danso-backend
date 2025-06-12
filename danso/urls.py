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
from leaderboard.views import leaderboard_view
from sentence.views import sentences, sentence_detail

urlpatterns = [
    path("admin/", admin.site.urls),
    path("leaderboard/", leaderboard_view),
    path("sentences/", sentences, name="sentences"),
    path("sentences/<int:sentence_id>/", sentence_detail, name="sentence_detail"),
]
