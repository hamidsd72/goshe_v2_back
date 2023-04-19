from rest_framework import routers
from .views import ( CategoryViewSet ,NotifyViewSet ,TransactionViewSet ,MessageViewSet, CreateMessageViewSet ,FollowerViewSet ,
CreateFollowerViewSet ,AuthorViewSet ,UserAuthorViewSet ,CreateAuthorViewSet ,CommentViewSet ,DocumentViewSet ,AdminUserAuthorViewSet ,
AdminAuthorViewSet ,AdminTransactionViewSet ,UserRegisterShiftUsingAuthorViewSet ,AuthorShiftViewSet ,AuthorShiftListViewSet,
 CreateExamViewSet, UserExamForAuthorViewSet, QuestionsExamViewSet, VisitExamViewSet, CreateVisitExamViewSet
)

app_name = 'api'
router = routers.SimpleRouter()
router.register(r'category', CategoryViewSet)
router.register(r'notify', NotifyViewSet)
router.register(r'transaction', TransactionViewSet)
router.register(r'admin-transaction', AdminTransactionViewSet)
router.register(r'message', MessageViewSet)
router.register(r'createmessage', CreateMessageViewSet)
router.register(r'follower', FollowerViewSet)
router.register(r'createfollower', CreateFollowerViewSet)
router.register(r'author', AuthorViewSet)
router.register(r'userauthor', UserAuthorViewSet)
router.register(r'adminuserauthor', AdminUserAuthorViewSet)
router.register(r'adminauthor', AdminAuthorViewSet)
router.register(r'createauthor', CreateAuthorViewSet)
router.register(r'comment', CommentViewSet) 
router.register(r'document', DocumentViewSet)

router.register(r'exam', CreateExamViewSet)
router.register(r'users/exam', UserExamForAuthorViewSet)
router.register(r'question', QuestionsExamViewSet)
router.register(r'visit/exam', VisitExamViewSet)
router.register(r'create/visit/exam', CreateVisitExamViewSet)

router.register(r'user-register-shift-using-author', UserRegisterShiftUsingAuthorViewSet)
router.register(r'author-shift', AuthorShiftViewSet)
router.register(r'author-shift-list', AuthorShiftListViewSet)
urlpatterns = router.urls
