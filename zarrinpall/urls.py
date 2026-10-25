from django.urls import path
from .views import payment, verify, parspalCallBack, parspalCreate
from payment.paystar_views import PaystarCreateView

urlpatterns = [
    path('gateway/payment2/', payment.as_view(), name='payment2'),
    path('gateway/verify/payment2/', verify.as_view() , name='verify'),
    # Compatibility for already-deployed frontends; old callbacks stay intact.
    path('gateway/parspal/create/link/', PaystarCreateView.as_view() , name='parspal_create_link'),
    path('gateway/parspal/verify/', parspalCallBack.as_view() , name='parspal_verify'),
]
