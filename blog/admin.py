from django.contrib import admin
from .models import Blog

class BlogAdmin(admin.ModelAdmin):
    list_display        = ('id','status','subject','content','baner','AuthorId','category_to_str','created_at','updated_at','jpublish','stars')

    def category_to_str(self, obj):
        return ", ".join([ category.title for category in obj.category.all() ])
    category_to_str.short_description = "دسته بندی"

    list_filter         = (['status','category','AuthorId'])
    search_fields       = ('AuthorId','subject','category','slug')
    # prepopulated_fields = {'slug': ('title',)}
    ordering            = ['status','category'] 

admin.site.register(Blog, BlogAdmin)