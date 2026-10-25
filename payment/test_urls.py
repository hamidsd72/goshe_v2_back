from django.urls import include, path

urlpatterns = [
    path("", include("payment.urls")),
    path("", include("zarrinpall.urls")),
]
