from django.contrib import admin
from .models import Category, Author, Message, Comment, Follower, Notify, Transaction, Document, CreateExam, QuestionsExam, VisitExam, AnswerVisitedExam, AuthorVisit

class CategoryAdmin(admin.ModelAdmin):
    list_display        = ('id','title','slug','status','category')
    list_filter         = (['slug'])
    search_fields       = ('title','slug')
    prepopulated_fields = {'slug': ('title',)} #create auto copy field => slug copy as title
    ordering            = ['slug'] 

admin.site.register(Category, CategoryAdmin)
# ====================================================================================
class DocumentAdmin(admin.ModelAdmin):
    list_display        = ('id','title')
    # list_filter         = (['title'])
    # search_fields       = ('title')
    # prepopulated_fields = {'status': ('title',)}
    ordering            = ['-id'] 

admin.site.register(Document, DocumentAdmin)
# ====================================================================================
class AuthorAdmin(admin.ModelAdmin):
    list_display        = ('id','userId','uid','call_price','msg_price','shaba',
        'status','older','visit_type','services','created_at','updated_at','category_to_str')

    def category_to_str(self, obj):
        return ", ".join([ category.title for category in obj.category.all() ])
    category_to_str.short_description = "دسته بندی" 

    list_filter         = (['services'])
    search_fields       = ('status','userId')
    # prepopulated_fields = {'slug': ('title',)}
    ordering            = ['status']

admin.site.register(Author, AuthorAdmin)
# ====================================================================================
class MessageAdmin(admin.ModelAdmin):
    list_display        = ('id','userId','type','sendTo','content','attach','amount','created_at','updated_at')
    list_filter         = (['type'])

admin.site.register(Message, MessageAdmin)
# ====================================================================================
class CommentAdmin(admin.ModelAdmin):
    list_display        = ('id','userId','authorId','stars','content','created_at','updated_at',)
    list_filter         = (['stars'])

admin.site.register(Comment, CommentAdmin)
# ====================================================================================
class FollowerAdmin(admin.ModelAdmin):
    list_display        = ('id','userId','followId','created_at','updated_at',)
    list_filter         = (['followId'])

admin.site.register(Follower, FollowerAdmin)
# ====================================================================================
class NotifyAdmin(admin.ModelAdmin):
    list_display        = ('id','userId','title','content','type','created_at','updated_at',)
    list_filter         = (['type'])

admin.site.register(Notify, NotifyAdmin)
# ====================================================================================
class TransactionAdmin(admin.ModelAdmin):
    list_display        = ('id','userId','amount','type','created_at','updated_at')
    list_filter         = (['type'])

admin.site.register(Transaction, TransactionAdmin)
# ====================================================================================
class CreateExamAdmin(admin.ModelAdmin):
    list_display  = "authorId", "userId", "name", "status", "slug", "amount", "created_at", "updated_at"

    list_filter   = (['authorId','status'])
    search_fields = ('authorId','status','name')
    ordering      = ['status']

admin.site.register(CreateExam, CreateExamAdmin)
# ====================================================================================
class QuestionsExamAdmin(admin.ModelAdmin):
    list_display  = "examId", "question", "type", "optionA", "optionB", "optionC", "optionD", "baner", "created_at", "updated_at"

    # list_filter   = (['examId','type'])
    # search_fields = ('examId','type')
    # ordering      = ['type']

admin.site.register(QuestionsExam, QuestionsExamAdmin)
# ====================================================================================
class VisitExamAdmin(admin.ModelAdmin):
    list_display  = "userId", "authorAnswer", "active", "created_at", "updated_at","examId"

    list_filter   = (['active'])
    search_fields = ('userId',)
    ordering      = ['active','created_at']

admin.site.register(VisitExam, VisitExamAdmin)
# ====================================================================================
class AnswerVisitedExamAdmin(admin.ModelAdmin):
    list_display  = "userId", "examId", "questionId", "answer"

    # list_filter   = (['examId'])
    # search_fields = ('examId','userId',)
    # ordering      = ['examId']

admin.site.register(AnswerVisitedExam, AnswerVisitedExamAdmin)
# ====================================================================================
class AuthorVisitAdmin(admin.ModelAdmin):
    list_display  = "AuthorId","AuthorUserId","userId","number","visitTime","active","autoDial","created_at","updated_at"

    list_filter   = (['active'])
    search_fields = ('AuthorId','userId')
    ordering      = ['-active','created_at']

admin.site.register(AuthorVisit, AuthorVisitAdmin)
# ====================================================================================
