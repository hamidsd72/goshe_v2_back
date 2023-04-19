from django.contrib.auth import get_user_model
from rest_framework import serializers

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model() 
        exclude = ("timer","code","user_permissions","groups","date_joined","is_staff","is_active","last_login","password","email","is_author","link")

class MyUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model() 
        # exclude = ("timer","code","amount","is_superuser","user_permissions","groups","date_joined","is_staff","is_active","last_login","password")
        fields = ["id","username","first_name","last_name","email","is_author","link","avatar","birthDay","codeMelly","province","city","address","jpublish"]

class CrUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id","username","timer","code","jpublish"]

class UserAmountSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id","username","amount","is_superuser","jpublish"]

