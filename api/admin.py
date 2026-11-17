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

    list_filter         = ('services', 'status')
    search_fields       = ('userId__username', 'userId__first_name', 'userId__last_name')
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
    search_fields       = ('userId','amount')
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
    search_fields = ('AuthorUserId__username','userId__username')
    ordering      = ['-active','created_at']

    def get_readonly_fields(self, request, obj=None):
        if obj and hasattr(obj, 'credit'):
            return [field.name for field in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(AuthorVisit, AuthorVisitAdmin)

from .models import ReservationCredit, ReservationNotification


class ReservationCreditAdmin(admin.ModelAdmin):
    list_display = ('id', 'payer', 'consultant', 'duration', 'amount_rial', 'refunded_rial', 'status', 'failure_code')
    list_filter = ('status',)
    search_fields = ('payer__username', 'consultant__username')

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReservationNotificationAdmin(ReservationCreditAdmin):
    list_display = ('id', 'credit', 'kind', 'status', 'attempts', 'receipt', 'updated_at')
    search_fields = ('credit__payer__username', 'credit__consultant__username')


admin.site.register(ReservationCredit, ReservationCreditAdmin)
admin.site.register(ReservationNotification, ReservationNotificationAdmin)
# ====================================================================================
