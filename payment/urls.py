from django.urls import path

from .paystar_views import PaystarCallbackView, PaystarConfirmView, PaystarCreateView

urlpatterns = [
    path("gateway/paystar/create/link/", PaystarCreateView.as_view(), name="paystar-create"),
    path("gateway/paystar/verify/", PaystarCallbackView.as_view(), name="paystar-verify"),
    path("gateway/paystar/confirm/", PaystarConfirmView.as_view(), name="paystar-confirm"),
]
