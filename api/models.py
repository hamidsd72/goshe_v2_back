from django.db import models
from account.models import User
from extensions.utils import jalali_converter

class Category(models.Model):
	title    = models.CharField(max_length=250, verbose_name="عنوان")
	slug     = models.SlugField(max_length=100, unique=True,verbose_name="اسلاگ")
	baner    = models.ImageField(upload_to="baner", verbose_name="بنر")
	category = models.IntegerField(null=True, default=1, verbose_name="دسته بندی")
	status   = models.BooleanField(default=True, verbose_name="نمایش")

	class Mete:
		verbose_name = "تخصص"
		verbose_name_plural = "تخصص ها"
	def __str__(self):
		return self.title

class Document(models.Model):
	userId = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userDocument", verbose_name="کاربر")
	title  = models.CharField(max_length=100, verbose_name="عنوان")
	baner  = models.ImageField(upload_to="document", verbose_name="تصویر")

	class Mete:
		verbose_name = "مدرک"
		verbose_name_plural = "مدارک"

	def __str__(self):
		return self.title+' - '+str(self.userId)

class Notify(models.Model):
	status_choices = (('o','one'), ('t','two'),('r','tree'))
	userId     = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userNotify", verbose_name="کاربر")
	type	   = models.CharField(max_length=1,default='o', choices=status_choices, verbose_name="نوع")
	title 	   = models.CharField(max_length=250, verbose_name="عنوان")
	content    = models.TextField(max_length=2500,null=True, verbose_name="محتوا")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Mete:
		verbose_name = "اعلان"
		verbose_name_plural = "اعلان ها"
	def __str__(self):
		return self.title+' - '+str(self.userId)

class Transaction(models.Model):
	status_choices = ( ('p','پیش فاکتور'), ('b','خرید'), ('s','تکمیل شده'), ('w','بازپرداخت'),('g','هدیه') )
	userId     = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userTransaction", verbose_name="کاربر")
	authorLink = models.CharField(null=True, max_length=200, verbose_name="ادرس مشاور")
	amount     = models.IntegerField(default=0, verbose_name="مبلغ")
	type       = models.CharField(max_length=1,default='p', choices=status_choices, verbose_name="نوع")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	idPay_id   = models.CharField(max_length=250, null=True, verbose_name="شماره آیدی پی")
	link       = models.CharField(max_length=250, null=True, verbose_name="لینک آیدی پی")

	status     = models.IntegerField(null=True, verbose_name="وضعیت آیدی پی")
	track_id   = models.CharField(null=True, max_length=250, verbose_name="کد رهگیری آیدی پی")
	card_no    = models.CharField(max_length=250, null=True, verbose_name="شماره کارت پرداخت")
	payment    = models.CharField(max_length=250, null=True, verbose_name="اطلاعات پرداخت تراکنش آیدی پی")
	
	class Mete:
		verbose_name = "تراکنش"
		verbose_name_plural = "تراکنش ها"

	def __str__(self):
		return self.type+' - '+str(self.userId)

	def jpublish(self):
		return jalali_converter(self.created_at)

	jpublish.short_description = 'تاریخ تولید'

class Message(models.Model):
	status_choices = (('n','normal'), ('s','special'))
	userId     = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userMessage", verbose_name="کاربر")
	sendTo     = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="sendToMessage", verbose_name="ارسال به")
	type       = models.CharField(max_length=1, default='n', choices=status_choices, verbose_name="نوع")
	amount     = models.IntegerField(null=True, verbose_name="قیمت پیام")
	content    = models.TextField(null=True, verbose_name="محتوا")
	status     = models.BooleanField(default=True, verbose_name="هنوز ندیده")
	attach 	   = models.ImageField(upload_to="files", null=True, verbose_name="فایل")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Mete:
		verbose_name = "پیام"
		verbose_name_plural = "پیام ها"
	def __str__(self):
		return self.content+' - '+str(self.userId)

class Follower(models.Model):
	userId      = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userId", verbose_name="کاربر")
	followId    = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userFollower", verbose_name="فالوور")
	requestUser = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="requestUserId")
	created_at  = models.DateTimeField(auto_now_add=True)
	updated_at  = models.DateTimeField(auto_now=True)

	class Mete:
		verbose_name = "فالوور"
		verbose_name_plural = "فالوور ها"

	def __str__(self):
		return str(self.userId)
	
	def jpublish(self):
		return jalali_converter(self.created_at)

	jpublish.short_description = 'تاریخ تولید'

class Author(models.Model):
	status_choices = (('m','message'), ('c','call'), ('b','both'))
	userId     = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userAuthor", verbose_name="کاربر")
	shaba      = models.CharField(max_length=50, null=True, verbose_name="شبا")
	category   = models.ManyToManyField(Category, verbose_name="دسته بندی")
	uid        = models.IntegerField(default=0, verbose_name="شماره جواز کار")
	call_price = models.IntegerField(default=0, verbose_name="نرخ تماس")
	msg_price  = models.IntegerField(default=0, verbose_name="نرخ پیام")
	status     = models.BooleanField(default=False, verbose_name="وضعیت")
	older      = models.TextField(max_length=2500, null=True, verbose_name="سابقه")
	oneDay     = models.CharField(max_length=250, null=True, verbose_name="روز اول")
	twoDay     = models.CharField(max_length=250, null=True, verbose_name="روز دوم")
	treeDay    = models.CharField(max_length=250, null=True, verbose_name="روز سوم")
	fourDay    = models.CharField(max_length=250, null=True, verbose_name="روز چهار")
	fiveDay    = models.CharField(max_length=250, null=True, verbose_name="روز پنج")
	sixDay     = models.CharField(max_length=250, null=True, verbose_name="روز شش")
	sevenDay   = models.CharField(max_length=250, null=True, verbose_name="روز هفت")
	visit_type = models.CharField(max_length=1, default='c', choices=status_choices, verbose_name="نوع ویزیت")
	certificate = models.CharField(null=True,max_length=50, verbose_name="مدرک تحصیلی")
	services   = models.BooleanField(default=False, verbose_name="نوع سرویس")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Mete:
		verbose_name = "نویسنده"
		verbose_name_plural = "نویسنده ها"
		
	def __str__(self):
		return str(self.userId)
		
class Comment(models.Model):
	userId     = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userComment", verbose_name="کاربر")
	authorId   = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="AuthorDoctorId", verbose_name="کارمند")
	stars      = models.IntegerField(null=True, default=3, verbose_name="سناره")
	content    = models.TextField(null=True, verbose_name="محتوا")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Mete:
		verbose_name = "کامنت"
		verbose_name_plural = "کامنت ها"
	def __str__(self):
		return self.content+' - '+str(self.userId)


# ----------------------------------------------------------
class Question(models.Model):
	status_choices = ( ('d','پیش نویس'), ('p','منتشر شده'), ('e','ویرایش شده') )
	authorId   = models.ForeignKey(Author, null=True, on_delete=models.SET_NULL, related_name="authorQuestion", verbose_name="مشاور")
	userId     = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userQuestion", verbose_name="کاربر")
	status     = models.CharField(max_length=1,default='d', choices=status_choices, verbose_name="وضعیت")
	slug       = models.SlugField(null=True,max_length=100, unique=True,verbose_name="اسلاگ")
	question   = models.CharField(max_length=250, verbose_name="سوال")
	type       = models.BooleanField(default=True, verbose_name="چهارگزینه ای")
	optionA    = models.CharField(blank=True, null=True, max_length=250, verbose_name="الف")
	optionB    = models.CharField(blank=True, null=True, max_length=250, verbose_name="ب")
	optionC    = models.CharField(blank=True, null=True, max_length=250, verbose_name="ج")
	optionD    = models.CharField(blank=True, null=True, max_length=250, verbose_name="د")
	amount     = models.IntegerField(default=0, verbose_name="قیمت")
	baner      = models.ImageField(upload_to="question" ,blank=True ,null=True ,verbose_name="بنر" )
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
    
	class Mete:
		verbose_name= "سوال"
		verbose_name_plural= "سوالات"

	def __str__(self):
		return self.question

class Exam(models.Model):
	userId     = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userExam", verbose_name="کاربر")
	questionId = models.ForeignKey(Question, null=True, on_delete=models.SET_NULL, related_name="questionId", verbose_name="سوال")
	answer     = models.CharField(null=True ,max_length=250, verbose_name="جواب")
	active     = models.BooleanField(default=False, verbose_name="پرداخت شده")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Mete:
		verbose_name= "آزمون"
		verbose_name_plural= "آزمون ها"

	def __str__(self):
		return str(self.userId)
# ----------------------------------------------------------


class CreateExam(models.Model):
	status_choices = ( ('d','پیش نویس'), ('p','منتشر شده'), ('e','ویرایش شده') )
	authorId   = models.ForeignKey(Author, null=True, on_delete=models.SET_NULL, related_name="authorCreateExam", verbose_name="مشاور")
	userId     = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userIdauthorCreateExam", verbose_name="کاربر")
	name       = models.CharField(null=True ,max_length=250, verbose_name="نام آزمون")
	status     = models.CharField(max_length=1 ,default='d', choices=status_choices, verbose_name="وضعیت")
	slug       = models.SlugField(null=True ,max_length=100, unique=True,verbose_name="اسلاگ")
	amount     = models.IntegerField(default=0, verbose_name="قیمت")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
    
	class Mete:
		verbose_name= "سوال"
		verbose_name_plural= "سوالات"

	def __str__(self):
		return str(self.slug)

class QuestionsExam(models.Model):
	examId     = models.ForeignKey(CreateExam, null=True, on_delete=models.SET_NULL, related_name="questionForExamId", verbose_name="سوال")
	question   = models.CharField(max_length=250, verbose_name="متن سوال")
	type       = models.BooleanField(default=True, verbose_name="چهارگزینه ای")
	optionA    = models.CharField(blank=True, null=True, max_length=250, verbose_name="الف")
	optionB    = models.CharField(blank=True, null=True, max_length=250, verbose_name="ب")
	optionC    = models.CharField(blank=True, null=True, max_length=250, verbose_name="ج")
	optionD    = models.CharField(blank=True, null=True, max_length=250, verbose_name="د")
	baner      = models.ImageField(upload_to="question" ,blank=True ,null=True ,verbose_name="بنر" )
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Mete:
		verbose_name= "تکه های سوال"
		verbose_name_plural= "تکه های سوالات"

	def __str__(self):
		return self.question

class VisitExam(models.Model):
	userId       = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userVisitedExam", verbose_name="کاربر")
	examId       = models.ForeignKey(CreateExam, null=True, on_delete=models.SET_NULL, related_name="examVisitId", verbose_name="سوال")
	authorAnswer = models.CharField(null=True,max_length=250, verbose_name="پاسخ مشاور")
	active       = models.BooleanField(default=False, verbose_name="پرداخت شده")
	created_at   = models.DateTimeField(auto_now_add=True)
	updated_at   = models.DateTimeField(auto_now=True)

	class Mete:
		verbose_name= "آزمون"
		verbose_name_plural= "آزمون ها"

	def __str__(self):
		return str(self.userId)

class AnswerVisitedExam(models.Model):
	userId      = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userAnsweredQuestion", verbose_name="کاربر")
	examId      = models.ForeignKey(CreateExam, null=True, on_delete=models.SET_NULL, related_name="examId", verbose_name="تست")
	questionId  = models.ForeignKey(QuestionsExam, null=True, on_delete=models.SET_NULL, related_name="answerQuestionId", verbose_name="سوال")
	answer      = models.CharField(null=True ,max_length=250, verbose_name="جواب")

	def __str__(self):
		return self.answer

	class Mete:
		verbose_name= "جواب های آزمون"
		verbose_name_plural= "جواب های آزمون ها"

class AuthorVisit(models.Model):
	AuthorId     = models.ForeignKey(Author, null=True, on_delete=models.SET_NULL, related_name="authorWasVisited", verbose_name="کد ویزیت مشاور")
	AuthorUserId = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="authorUserIdWasVisited", verbose_name="کد کاربری مشاور")
	userId       = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="userRequest", verbose_name="کاربر متقاضی")
	number       = models.CharField(max_length=10, verbose_name="شماره تماس")
	visitTime    = models.DateTimeField(verbose_name="زمان ویزیت")
	active       = models.BooleanField(default=False, verbose_name="تایید مشاور")
	autoDial     = models.BooleanField(default=False, verbose_name="تماس خودکار")
	created_at   = models.DateTimeField(auto_now_add=True)
	updated_at   = models.DateTimeField(auto_now=True)

	def jpublish(self):
		return jalali_converter(self.visitTime)

	jpublish.short_description = 'تاریخ تولید'
	