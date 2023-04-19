from django.db import models
from api.models import Author, Category
from extensions.utils import jalali_converter

class Blog(models.Model):
    status_choices = ( ('d','پیش نویس'), ('p','منتشر شده'), ('e','ویرایش شده') )
    AuthorId   = models.ForeignKey(Author, null=True, on_delete=models.SET_NULL, related_name="authorId", verbose_name="نویسنده")
    category   = models.ManyToManyField(Category, verbose_name="دسته بندی")
    status     = models.CharField(max_length=1,default='d', choices=status_choices, verbose_name="وضعیت")
    slug       = models.SlugField(null=True,max_length=100, unique=True,verbose_name="اسلاگ")
    stars      = models.IntegerField(null=True,verbose_name="ستاره")
    subject    = models.CharField(max_length=250, verbose_name="عنوان")
    content    = models.TextField(max_length=5000, verbose_name="محتوا")
    baner      = models.ImageField(upload_to="blog", verbose_name="بنر")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Mete:
        verbose_name= "مقاله"
        verbose_name_plural= "مقالات"

    def __str__(self):
        return self.subject+' - '+str(self.AuthorId)

    def jpublish(self):
        return jalali_converter(self.created_at)

    jpublish.short_description = 'تاریخ تولید'


