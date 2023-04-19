from django.db import models
from account.models import User
from extensions.utils import jalali_converter

class Ticket(models.Model):
    userId     = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="ticketUserId", verbose_name="کاربر")
    sendTo     = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="sendTicketToUserId", verbose_name="ارسال از ادمین به")
    subject    = models.CharField(max_length=250, verbose_name="عنوان")
    content    = models.TextField(max_length=2500, verbose_name="محتوا")
    baner      = models.ImageField(null=True, upload_to="ticket", verbose_name="تصویر")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status     = models.BooleanField(default=False, verbose_name="وضعیت")
    
    class Mete:
        verbose_name = "تیکت"
        verbose_name_plural = "تیکت ها"
    
    def __str__(self):
        return self.subject
    
    def jpublish(self):
        return jalali_converter(self.created_at)

    jpublish.short_description = 'تاریخ تولید'
    



