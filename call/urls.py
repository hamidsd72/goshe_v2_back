from rest_framework import routers
from .views import CallLogViewSet ,AdminShowUserCallView, AdminShowUserMessageView, NumbersViewSet, ActiveCallLogViewSet, CallLogViewSet_v2

app_name = 'call'
router = routers.SimpleRouter()
router.register(r'callLog-v2', CallLogViewSet_v2)
router.register(r'callLog', CallLogViewSet)
router.register(r'numbers', NumbersViewSet)
router.register(r'AdminShowUserCall', AdminShowUserCallView)
router.register(r'AdminShowUserMessage', AdminShowUserMessageView)
router.register(r'ActiveCallLog', ActiveCallLogViewSet)
urlpatterns = router.urls
 
