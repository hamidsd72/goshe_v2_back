"""Restricted adapter around django-log-viewer; serve only our known log files."""
from functools import wraps
from pathlib import Path
import re
from django.conf import settings
from django.contrib.admin.utils import unquote
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpResponseForbidden
from django.urls import re_path, reverse
from django.views.decorators.cache import never_cache
from log_viewer import views

app_name = 'log_viewer'


def checked_file(name):
    base = Path(settings.LOG_VIEWER_FILES_DIR).resolve()
    name = unquote(name)
    if not re.fullmatch(r'project\.log(?:\.\d+)?', name):
        raise Http404
    path = base / name
    if path.is_symlink() or path.resolve().parent != base or not path.is_file():
        raise Http404


def private_view(view):
    @wraps(view)
    @never_cache
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse('admin:login'))
        if not request.user.is_active or not request.user.is_superuser:
            return HttpResponseForbidden()
        name = kwargs.get('file_name') or request.GET.get('file_name')
        if name:
            checked_file(name)
        if int(kwargs.get('page', 1)) < 1 or int(kwargs.get('page', 1)) > 1000:
            raise Http404
        # The upstream ZIP reader walks directories. Reject unexpected files/links first.
        base = Path(settings.LOG_VIEWER_FILES_DIR)
        if base.exists():
            for path in base.rglob('*'):
                if path.is_symlink() or path.is_dir():
                    raise Http404
                if path.name.startswith('project.log'):
                    checked_file(path.name)
        return view(request, *args, **kwargs)
    return wrapped


urlpatterns = [
    re_path(r'^$', private_view(views.log_viewer), name='log_file_view'),
    re_path(r'^json/(?P<file_name>[.\w-]*)/(?P<page>[0-9]+)$', private_view(views.log_json), name='log_json_view'),
    re_path(r'^json/(?P<file_name>[.\w-]*)$', private_view(views.log_json), name='log_json_view'),
    re_path(r'^download/single-file/$', private_view(views.log_download), name='log_download_file_view'),
    re_path(r'^download.zip$', private_view(views.log_download), name='log_download_zip_view'),
]
