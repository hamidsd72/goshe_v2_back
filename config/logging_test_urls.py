from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


def crash(request, private):
    raise RuntimeError('secret=must-not-be-logged; private consultation')


class HandledError(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        raise ValidationError({'detail': 'invalid input'})


urlpatterns = [
    path('admin/project-logs/', include('config.log_urls')),
    path('admin/', admin.site.urls),
    path('probe/ok/', lambda r: HttpResponse('ok')),
    path('probe/crash/<str:private>/', crash),
    path('probe/error/', HandledError.as_view()),
    path('', include('api.reservation_regression_test_urls')),
]
