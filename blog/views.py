from .models import Blog
from .serializers import BlogSerializer, CreatePostSerializer
from rest_framework.viewsets import ModelViewSet
from api.permissions import IsIdOrReadOnly, IsSuperUserOrReadOnly

class letestBlogViewSet(ModelViewSet):
    queryset = Blog.objects.exclude(status='d').order_by('-id')
    serializer_class = BlogSerializer
    permission_classes = [IsIdOrReadOnly]

    def get_queryset(self):
        queryset = Blog.objects.exclude(status='d').order_by('-id')

        category = self.request.query_params.get('category')
        if category is not None:
            queryset = queryset.filter(category=category)[:10]

        letest = self.request.query_params.get('letest')
        if letest is not None:
            queryset = queryset.exclude(status='d').order_by('-id')[:5]

        return queryset

class BlogViewSet(ModelViewSet):
    queryset = Blog.objects.exclude(status='d').order_by('-id')
    serializer_class = BlogSerializer
    permission_classes = [IsSuperUserOrReadOnly]

class CreatePostViewSet(ModelViewSet):
    queryset = Blog.objects.exclude(status='d').order_by('-id')
    serializer_class = CreatePostSerializer
    permission_classes = [IsIdOrReadOnly]