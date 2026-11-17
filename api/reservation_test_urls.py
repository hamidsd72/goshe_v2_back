from django.urls import include, path
from call.views import UpdateCallCreateViewSet, CallCreateViewSet

urlpatterns = [path('', include('api.urls')),
    path('update_call/', UpdateCallCreateViewSet.as_view()),
    path('call_create/', CallCreateViewSet.as_view())]
