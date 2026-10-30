from rest_framework import routers
from .views import (FollowerViewSet)
from django.urls import path

app_name = 'message'

router = routers.SimpleRouter()
urlpatterns = router.urls
urlpatterns += path('follower', FollowerViewSet.as_view()),
