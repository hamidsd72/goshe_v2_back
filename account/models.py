# from typing import _SpecialForm
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from extensions.utils import jalali_converter

class User(AbstractUser):
    is_author    = models.BooleanField(default=False, verbose_name="کارمند بودن")
    special_user = models.DateTimeField(default=timezone.now, verbose_name="کاربر ویژه")
    amount       = models.IntegerField(default=0,verbose_name="موجودی")
    link         = models.IntegerField(null=True, verbose_name="واسط")
    avatar       = models.ImageField(upload_to="avatar", null=True, verbose_name="آواتار")
    timer        = models.DateTimeField(default=timezone.now)
    code         = models.IntegerField(null=True)
    birthDay     = models.CharField(null=True,max_length=12,verbose_name="تاریخ تولد")
    codeMelly    = models.CharField(null=True,max_length=10,verbose_name="کد ملی")
    province     = models.CharField(null=True,max_length=100,verbose_name="استان")
    city         = models.CharField(null=True,max_length=100,verbose_name="شهر")
    address      = models.CharField(null=True,max_length=250,verbose_name="آدرس")

    def is_special_user(self):
        if self.special_user > timezone.now():
            return True
        else:
            return False

    def jpublish(self):
        return jalali_converter(self.date_joined)

    jpublish.short_description = 'تاریخ تولید'
    
