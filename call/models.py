from django.db import models
from account.models import User
from extensions.utils import jalali_converter

class CallLog(models.Model):
	Sitak_id     = models.IntegerField(null=True, verbose_name="شماره سیتک")
	userId       = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userCallLog", verbose_name="کاربر")
	authorId     = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="DoctorCallId", verbose_name="کارمند")
	type         = models.CharField(max_length=50,default="در حال تماس", verbose_name="نوع تماس")
	FirstCredit  = models.IntegerField(null=True,verbose_name="شارژ اولیه")
	call_amount  = models.IntegerField(null=True,verbose_name="هزینه تماس")
	AmountPerMin = models.IntegerField(null=True,verbose_name="هزینه هر دقیقه")
	created_at   = models.DateTimeField(auto_now_add=True)
	updated_at   = models.DateTimeField(auto_now=True)

	class Mete:
		verbose_name = "گزارش"
		verbose_name_plural = "گزارش ها"
	
	def __str__(self):
		return str(self.userId)

	def jpublish(self):
		return jalali_converter(self.created_at)

	jpublish.short_description = 'تاریخ تولید'

class Number(models.Model):
	userId     = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userSubNumber", verbose_name="کاربر")
	number     = models.CharField(max_length=10, verbose_name="شماره")
	subject    = models.CharField(null=True,max_length=100, verbose_name="عنوان")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Mete:
		verbose_name = "شماره"
		verbose_name_plural = "شماره ها"
	
	def __str__(self):
		return str(self.userId)

	def jpublish(self):
		return jalali_converter(self.created_at)

	jpublish.short_description = 'تاریخ تولید'