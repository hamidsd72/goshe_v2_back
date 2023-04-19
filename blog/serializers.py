from .models import Blog
from api.models import Author
from django.contrib.auth import get_user_model
from rest_framework import serializers

class UserArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['first_name','last_name']

class AuthorArticleSerializer(serializers.ModelSerializer):
    userId = UserArticleSerializer()
    class Meta:
        model = Author
        fields = ['userId',]
        
class BlogSerializer(serializers.ModelSerializer):
    AuthorId = AuthorArticleSerializer()
    class Meta:
        model = Blog
        fields = ['id','AuthorId','subject','slug','stars','content','baner','jpublish','category']

class CreatePostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = ['id','AuthorId','subject','slug','stars','content','baner','category']