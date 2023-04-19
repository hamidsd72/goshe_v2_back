from django.urls import path
from .views import payment, verify, parspalCallBack, parspalCreate

urlpatterns = [
    path('gateway/payment2/', payment.as_view(), name='payment2'),
    path('gateway/verify/payment2/', verify.as_view() , name='verify'),
    path('gateway/parspal/create/link/', parspalCreate.as_view() , name='parspal_create_link'),
    path('gateway/parspal/verify/', parspalCallBack.as_view() , name='parspal_verify'),
]