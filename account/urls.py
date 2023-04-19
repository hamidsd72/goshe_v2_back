from rest_framework import routers
from .views import UserViewSet, UserAmountViewSet, CrUserViewSet, AdminUserViewSet

app_name = 'account'
router = routers.SimpleRouter()
router.register(r'admin-user', AdminUserViewSet)
router.register(r'my-user', UserViewSet)
router.register(r'cr-user', CrUserViewSet)
router.register(r'amount-user', UserAmountViewSet)
urlpatterns = router.urls
