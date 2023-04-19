from django.contrib import admin
from django.urls import path, re_path, include
# for swagger
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
# for show media files
from django.conf import settings
from django.conf.urls.static import static

from api.views import ( SendViewSet, ProfileCountViewSet, FindAuthorListViewSet, NewestMessageViewSet, CompletedMessageViewSet, 
NewestFromUserMessageViewSet, FindAuthorByFamilyViewSet, AdminFindAuthorByUsernameViewSet, AnswerVisitedExamViewSet, AnswerVisitedExamViewSetNew,
 AnswerQuestionsViewSet, AnswerQuestionsViewSetNew, AuthorAnswerToVisitedExamViewSetNew, SendMessageViewSet )

from account.views import CreateCodeUserViewSet, GetCodeUserViewSet, CallCreateCodeUserViewSet, CreateTaskCallInTimeViewSet
from call.views import CallCreateViewSet, UpdateCallCreateViewSet, CallAndMessageLogView, AdminCallCreateViewSet, AdminCallAndMessageLogView, FlashCallLogViewSet
from payment.views import PaymentCreateViewSet, IdPayCallBack, PaymentExamViewSet
from ticket.views import AdminTicketViewSet, SendAdminMsgToUserViewSet

# from zarrinpall.views import payment, verify

# for swagger
schema_view = get_schema_view(
   openapi.Info(
      title="JarchiParsi API",
      default_version='v1',
      description="for medical application",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="GPLv3 License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
   path('CreateTaskCallInTime/', CreateTaskCallInTimeViewSet.as_view()),
   path('send_massege/', SendViewSet.as_view()),
   path('notification-for-users', SendMessageViewSet.as_view()),
   path('countcomment/', ProfileCountViewSet.as_view()),
   path('create-code/', CreateCodeUserViewSet.as_view()),
   path('adminCallCreate/', AdminCallCreateViewSet.as_view()),
   path('call-create-code/', CallCreateCodeUserViewSet.as_view()),
   path('get-code/', GetCodeUserViewSet.as_view()),
   path('flash-call-create-code/', FlashCallLogViewSet.as_view()),
   path('call_create/', CallCreateViewSet.as_view()),
   path('update_call/', UpdateCallCreateViewSet.as_view()),

   path('payment_create/', PaymentCreateViewSet.as_view()),
   path('payment_verify/', IdPayCallBack.as_view()),
   path('payment-exam/', PaymentExamViewSet.as_view()),

   path('admin-ticket/', AdminTicketViewSet.as_view()),
  
   path('answer/visit/', AnswerVisitedExamViewSet.as_view()),
   path('answer/visit/new/', AnswerVisitedExamViewSetNew.as_view()),
   path('answer/question/visit/exam', AnswerQuestionsViewSet.as_view()),
   path('answer/question/visit/exam/new', AnswerQuestionsViewSetNew.as_view()),
   path('author/answer/to/visit/new/', AuthorAnswerToVisitedExamViewSetNew.as_view()),

   path('find_author_list/', FindAuthorListViewSet.as_view()),
   path('find_author_by_last_name_list/', FindAuthorByFamilyViewSet.as_view()),
   path('messageNotSee/', NewestMessageViewSet.as_view()),
   path('completedMessage/', CompletedMessageViewSet.as_view()),
   path('newestFromUserMessage/', NewestFromUserMessageViewSet.as_view()),
   path('callAndMessageLog/', CallAndMessageLogView.as_view()),
   path('admincallAndMessageLog/', AdminCallAndMessageLogView.as_view()),
   path('adminFindAuthorByUsername/', AdminFindAuthorByUsernameViewSet.as_view()),
   path('SendAdminMsgToUser/', SendAdminMsgToUserViewSet.as_view()),

   # path('payment2/', payment.as_view(), name='payment2'),
   # path('verify/payment2/', verify.as_view() , name='verify'),

   # my app 
   path('', include('blog.urls')),
   path('', include('call.urls')),
   path('', include('api.urls')),
   path('', include('account.urls')),
   path('', include('ticket.urls')),
   path('', include('zarrinpall.urls')),

   path('admin/', admin.site.urls),
   # for djoser
   path('api/auth/', include('djoser.urls')),
   path('api/auth/', include('djoser.urls.authtoken')),
   # swagger
   re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
   re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
   re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
