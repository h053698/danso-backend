"""
WSGI config for danso project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "danso.settings")
os.environ.setdefault("RAILPACK_DJANGO_APP_NAME", "danso")
os.environ.setdefault("RAILPACK_PYTHON_VERSION", "3.12")

application = get_wsgi_application()
