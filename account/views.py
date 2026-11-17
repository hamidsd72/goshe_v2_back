from .serializers import CrUserSerializer, MyUserSerializer, UserAmountSerializer, AdminUserSerializer
from .services import OtpDeliveryError, send_auth_otp
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.viewsets import ModelViewSet
from api.permissions import IsIdOrReadOnly
from api.permissions import IsSuperUserOrReadOnly, IsSuperUser
from random import randint
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView 
from rest_framework.response import Response
from datetime import timedelta
import requests

class CreateCodeUserViewSet(APIView):
    permission_classes = [AllowAny,]
    def post(self, request):
        try:
            username = str(request.data['username']).strip()
            user = get_user_model().objects.get(username=username)
        except (KeyError, get_user_model().DoesNotExist):
            return Response({"errors": "شماره یافت نشد"}, status=400)

        try:
            code = send_auth_otp(username)
        except OtpDeliveryError:
            return Response({"errors": "ارسال کد تایید ناموفق بود"}, status=503)

        user.code = code
        user.timer = timezone.now() + timedelta(seconds=settings.AUTH_OTP_TTL_SECONDS)
        user.save(update_fields=["code", "timer"])
        return Response({"msg": "کد جدید ایجاد شد"}, status=200)

class GetCodeUserViewSet(APIView):
    permission_classes = [AllowAny,]
    def post(self, request):
        try:
            user = get_user_model().objects.get(username=request.data['username'])
            if user.timer < timezone.now():
                return Response({"allow": False, "errors": "کد منقضی شده است"}, status=400)
            if user.code == int(request.data['code']):
                user.code = None
                user.save(update_fields=["code"])
                return Response({"allow": True}, status=200)
            # return Response({"allow": False,"code":getCodeSerializer.data["code"] }, status=200)
            return Response({"allow": False}, status=200)
        except (KeyError, TypeError, ValueError, get_user_model().DoesNotExist):
            return Response({"errors": "user not found"}, status=400)

class CallCreateCodeUserViewSet(APIView):
    permission_classes = [AllowAny,]
    def post(self, request):
        try:
            user = get_user_model().objects.get(username=request.data['username'])
            code = randint(100000, 999999)
        except:
            return Response({"errors": "شماره یافت نشد"}, status=400)
        
        data =  {"username": request.data['username'],"code": code}
        codeRefreshserializer = CrUserSerializer(user,data=data)
        if(codeRefreshserializer.is_valid()):
            codeRefreshserializer.save()
            try:
                url = "http://93.118.104.154:61200/dialer.php"

                payload={ 'code': codeRefreshserializer.data['code'], 'dst': "0"+codeRefreshserializer.data['username'] }

                files=[]

                headers = { 'Authorization': 'Basic c2l0YWs6d3EzMXcyM2R0U3d2ZnRocmVkZmdzNzhrbDg4N3Y5NWJjNjU0Qw==' }

                response = requests.request("POST", url, headers=headers, data=payload, files=files)
                return Response( response, status=200)
            except:
                return Response({"errors": "خطا در ارسال تماس"}, status=400) 

class CrUserViewSet(ModelViewSet):
    queryset = get_user_model().objects.all().order_by('-id')
    serializer_class = CrUserSerializer
    permission_classes = [IsIdOrReadOnly]

class UserViewSet(ModelViewSet):
    queryset = get_user_model().objects.all().order_by('-id')
    serializer_class = MyUserSerializer 
    permission_classes = [IsIdOrReadOnly]

class AdminUserViewSet(ModelViewSet):
    queryset = get_user_model().objects.all().order_by('-id')
    serializer_class = AdminUserSerializer 
    permission_classes = [IsSuperUser]

    def get_queryset(self):
        queryset = get_user_model().objects.all().order_by('-id')
        username = self.request.query_params.get('username')
        if username is not None:
            queryset = queryset.filter(username=username)

        return queryset

class UserAmountViewSet(ModelViewSet):
    queryset = get_user_model().objects.all().order_by('-id')
    serializer_class = UserAmountSerializer
    permission_classes = [IsSuperUserOrReadOnly]
