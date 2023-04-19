from rest_framework import routers
from .views import BlogViewSet, CreatePostViewSet, letestBlogViewSet

app_name = 'blog'
router = routers.SimpleRouter()
router.register(r'blog', BlogViewSet)
router.register(r'post', CreatePostViewSet)
router.register(r'letest-blog', letestBlogViewSet)
urlpatterns = router.urls