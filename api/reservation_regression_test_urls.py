from django.urls import include, path
from account.views import CreateCodeUserViewSet, GetCodeUserViewSet

urlpatterns = [path('', include('api.reservation_test_urls')),
    path('', include('payment.test_urls')),
    path('', include('consultant_accounting.urls')),
    path('create-code/', CreateCodeUserViewSet.as_view()),
    path('get-code/', GetCodeUserViewSet.as_view())]
