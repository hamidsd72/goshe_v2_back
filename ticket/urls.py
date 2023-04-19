from rest_framework import routers
from .views import TicketViewSet, AdminViewTicketViewSet, TicketViewSet2

app_name = 'ticket'
router = routers.SimpleRouter()
router.register(r'ticket', TicketViewSet)
router.register(r'ticket-v2', TicketViewSet2)
router.register(r'admin-view-ticket', AdminViewTicketViewSet)
urlpatterns = router.urls
