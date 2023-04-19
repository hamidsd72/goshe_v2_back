# from rest_framework import response
from .models import Category ,Notify ,Transaction ,Message ,Follower ,Author ,Comment ,Document, AuthorVisit, CreateExam, QuestionsExam, VisitExam, AnswerVisitedExam
# , Question, QuestionParts, Exam, ExamParts
from call.models import CallLog
from django.db.models import Sum
import math
import datetime
from .serializers import ( CategorySerializer ,NotifySerializer ,TransactionSerializer ,PaymentTransactionSerializer, HeadMessageSerializer ,
MessageSerializer ,FollowerSerializer ,CreateFollowerSerializer, AuthorSerializer ,CreateAuthorSerializer ,CommentSerializer ,DocumentSerializer,
 FindAuthorAuthorSerializer, AdminAuthorSerializer, AdminEditAuthorSerializer, VisitSerializer, AuthorVisitSerializer, AuthorVisitListSerializer,
 CreateExamSerializer ,QuestionsExamSerializer ,VisitExamSerializer ,CreateVisitExamSerializer ,CreateAnswerVisitedExamSerializer ,UserVisitExamForAuthorSerializer )

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny
# from .permissions import IsSuperUser, IsSuperUserOrReadOnly, IsStaffOrReadOnly, IsSuperUserOrStaffReadOnly, IsUserIdOrReadOnly
from .permissions import IsSuperUserOrReadOnly, IsUserIdOrReadOnly, IsSuperUser, IsAuthorUserIdOrReadOnly

from django.contrib.auth import get_user_model
from account.serializers import UserAmountSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
import os
from rest_framework.pagination import PageNumberPagination

class LargeResultsSetPagination(PageNumberPagination):
    page_size = 200
    page_size_query_param = 'page_size'
    max_page_size = 10000
# messages
class SendViewSet(APIView):
    def post(self, request):
        try:
            if request.data['isAuthor'] == 'notAuthor':
                sendToUser  = Author.objects.filter(userId=request.data['sendTo']).first()
                serializer1 = CreateAuthorSerializer(sendToUser)
                msgPrice    = serializer1.data['msg_price'] * 10
            else:
                msgPrice = 0
            
            authUser    = get_user_model().objects.get(id=self.request.user.id)
            serializer2 = UserAmountSerializer(authUser)
            amount      = serializer2.data['amount']
        except:
            return Response({"detail": "دسترسی مسدود شد"}, status=404)
        if request.user.amount >= msgPrice:
            serializer3 = MessageSerializer(data=request.data)
            if(serializer3.is_valid()):
                serializer3.save()
                amount -= msgPrice
                serializer4 = UserAmountSerializer(authUser,data={"amount": amount, "username": serializer2.data["username"]})
                if(serializer4.is_valid()):
                    serializer4.save()

                    msg = '''curl -X POST https://console.melipayamak.com/api/send/shared/1515c626310f4b529d6af64d0acedafe -H 'Content-Type: application/json' -d '{"bodyId": 74630, "to": '''+str('"0'+request.data['username']+'"')+''' ,"args": [] }' '''
                    os.system(msg)

                    return Response(serializer3.data, status=201)
                return Response(serializer4.errors, status=400)
            return Response(serializer3.errors, status=400)
        else:
            return Response({"detail": "اعتبار کافی نیست"}, status=404)
# =============================================================
class MessageViewSet(ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = HeadMessageSerializer
    permission_classes = [IsUserIdOrReadOnly]
    def get_queryset(self):
        queryset  = Message.objects.order_by('-id')
        sendTo    = self.request.query_params.get('followId')
        lastday   = self.request.query_params.get('lastday')
        if sendTo is not None:
            queryset = queryset.filter(userId=self.request.user.id).filter(sendTo=sendTo).order_by('-id') | queryset.filter(userId=sendTo).filter(sendTo=self.request.user.id).order_by('-id')

        if lastday is not None:
            date       = datetime.date.today()
            start_week = date - datetime.timedelta(int(lastday))
            end_week   = datetime.date.today()
            queryset = queryset.filter(created_at__range=[start_week, end_week])

        # return final
        return queryset
# =============================================================
class CreateMessageViewSet(ModelViewSet):
    queryset = Message.objects.all()
    def get_queryset(self):
        queryset = Message.objects.order_by('-id')
        sendTo   = self.request.query_params.get('followId')
        me       = self.request.query_params.get('me')
        if sendTo is not None:
            queryset = queryset.filter(userId=self.request.user.id).filter(sendTo=sendTo).order_by('-id') | queryset.filter(userId=sendTo).filter(sendTo=self.request.user.id).order_by('-id')
        if me is not None:
            queryset = queryset.filter(userId=self.request.user.id)
        return queryset
    
    serializer_class = MessageSerializer
    permission_classes = [IsUserIdOrReadOnly]
# =============================================================
class NewestMessageViewSet(APIView):
    def get(self, request):
        queryset = Message.objects.filter(sendTo=self.request.user.id).filter(status=False).count()
        return Response({'messageNotSee': queryset}, status=200)
# =============================================================
class NewestFromUserMessageViewSet(APIView):
    def post(self, request):
        queryset = Message.objects.filter(sendTo=self.request.user.id).filter(userId=request.data['userId']).filter(status=False).count()
        return Response({'messageNotSee': queryset}, status=200)
# =============================================================
class CompletedMessageViewSet(APIView):
    def post(self, request):
        queryset = Message.objects.filter(sendTo=self.request.user.id).filter(userId=request.data['userId']).filter(status=False)
        if queryset.count() > 0:
            for q in queryset:
                complete = MessageSerializer(q,data={"status": True})
                if(complete.is_valid()):
                    complete.save()
        return Response({'completedMessage': queryset.count()}, status=200)
# =============================================================
# categories
class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.filter(status=True)
    serializer_class = CategorySerializer
    permission_classes = [IsSuperUserOrReadOnly]

    def get_queryset(self):
        queryset = Category.objects.filter(status=True)

        category = self.request.query_params.get('category')
        if category is not None:
            queryset = queryset.filter(category=category)

        return queryset
# =============================================================
# authors dosuments
class DocumentViewSet(ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsUserIdOrReadOnly,]
# =============================================================
# users notifications
class NotifyViewSet(ModelViewSet):
    queryset = Notify.objects.all()
    serializer_class = NotifySerializer
    lookup_field = "slug"
    permission_classes = [IsSuperUserOrReadOnly]
    def get_queryset(self):
        queryset = Notify.objects.all().order_by('-id')
        userId = self.request.query_params.get('userId')
        if userId is not None:
            queryset = queryset.filter(userId=userId)

        return queryset
# =============================================================
# users transactions
class TransactionViewSet(ModelViewSet):
    queryset = Transaction.objects.filter(type='s').order_by('-id')
    serializer_class = TransactionSerializer
    permission_classes = [IsUserIdOrReadOnly]
    def get_queryset(self):
        queryset = Transaction.objects.filter(type='s').order_by('-id')
        userId = self.request.query_params.get('userId')
        if userId is not None:
            queryset = queryset.filter(userId=userId)

        return queryset
# =============================================================
class AdminTransactionViewSet(ModelViewSet):
    queryset = Transaction.objects.order_by('-id')
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsSuperUser]

    def get_queryset(self):
        queryset = Transaction.objects.order_by('-id')
        userId = self.request.query_params.get('userId')
        if userId is not None:
            queryset = queryset.filter(userId=userId)
        
        onlyW = self.request.query_params.get('onlyW')
        if onlyW is not None:
            queryset = queryset.filter(type='w')

        return queryset
# =============================================================
# users followed authors
class FollowerViewSet(ModelViewSet):
    queryset = Follower.objects.order_by('-id')
    serializer_class = FollowerSerializer
    permission_classes = [IsUserIdOrReadOnly]
    def get_queryset(self):
        queryset = Follower.objects.order_by('-id')

        userId = self.request.query_params.get('userId')
        if userId is not None:
            queryset = queryset.filter(userId=userId)

        return queryset
# =============================================================
class CreateFollowerViewSet(ModelViewSet):
    queryset = Follower.objects.all()
    serializer_class = CreateFollowerSerializer
    lookup_field = "userId"
    permission_classes = [IsUserIdOrReadOnly]
    def get_queryset(self):
        queryset = Follower.objects.all().order_by('id')

        userId = self.request.query_params.get('userId')
        if userId is not None:
            queryset = queryset.filter(userId=userId)
        followId = self.request.query_params.get('followId')
        if followId is not None:
            queryset = queryset.filter(followId=followId)

        return queryset
# =============================================================
# authors data
class AuthorViewSet(ModelViewSet):
    queryset = Author.objects.order_by('-id')
    serializer_class = AuthorSerializer
    # lookup_field = "slug"
    permission_classes = [IsUserIdOrReadOnly]

    def get_queryset(self):
        queryset = Author.objects.order_by('-services')

        status = self.request.query_params.get('status')
        if status is not None:
            queryset = queryset.filter(status=status)

        services = self.request.query_params.get('services')
        if services is not None:
            queryset = queryset.filter(services=services)

        category = self.request.query_params.get('category')
        if category is not None:
            queryset = queryset.filter(category__slug=category)

        visit_type = self.request.query_params.get('visit_type')
        if visit_type is not None:
            queryset = queryset.filter(visit_type=visit_type)

        return queryset
# =============================================================
class AdminUserAuthorViewSet(ModelViewSet):
    queryset = Author.objects.order_by('-id')
    serializer_class   = AdminAuthorSerializer
    permission_classes = [IsSuperUser]

    def get_queryset(self):
        queryset = Author.objects.order_by('-id')

        status   = self.request.query_params.get('status')
        lastday  = self.request.query_params.get('lastday')
        if status is not None:
            queryset = queryset.filter(status=status)

        if lastday is not None:
            date = datetime.date.today()
            start_week = date - datetime.timedelta(int(lastday))
            end_week   = datetime.date.today()
            queryset   = queryset.filter(created_at__range=[start_week, end_week])

        return queryset
# =============================================================
class AdminAuthorViewSet(ModelViewSet):
    queryset = Author.objects.order_by('-id')
    serializer_class = AdminEditAuthorSerializer
    # lookup_field = "slug"
    permission_classes = [IsSuperUser]

    def get_queryset(self):
        queryset = Author.objects.order_by('-id')

        status = self.request.query_params.get('status')
        if status is not None:
            queryset = queryset.filter(status=status)

        return queryset
# =============================================================
class AdminFindAuthorByUsernameViewSet(APIView):
    permission_classes = [IsSuperUser]
    def post(self, request):
        if not request.data['username']:
            return Response({'error': 'username is required'}, status=403)
        try:
            firstName = get_user_model().objects.filter(username=request.data['username'])
            lastName  = get_user_model().objects.filter(last_name=request.data['username'])
            userId = firstName | lastName
            if userId:
                usersId = []
                for user in userId:
                    usersId.append(user.id)
                authors = Author.objects.filter(userId__in=usersId)
                data_list = []
                for author in authors:
                    data_list.append(AdminAuthorSerializer(author).data)
                return Response(data_list, status=201)
        except:
            return Response({"error": "author by this number or last_name not found"}, status=404)
# =============================================================
class UserAuthorViewSet(ModelViewSet):
    queryset = Author.objects.order_by('-id')
    serializer_class = AuthorSerializer
    # lookup_field = "slug"
    permission_classes = [IsUserIdOrReadOnly]

    def get_queryset(self):
        queryset = Author.objects.order_by('-id')

        userId = self.request.query_params.get('userId') 
        if userId is not None:
            queryset = queryset.filter(userId=userId)

        return queryset
# =============================================================
class CreateAuthorViewSet(ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = CreateAuthorSerializer
    lookup_field = "userId"
    permission_classes = [IsUserIdOrReadOnly]

    def get_queryset(self):
        queryset = Author.objects.all()

        userId = self.request.query_params.get('userId')
        if userId is not None:
            queryset = queryset.filter(userId=userId)

        return queryset
# =============================================================
class FindAuthorListViewSet(APIView):
    def post(self, request):
        if not request.data['list']:
            return Response({'error': 'list is required'}, status=403)
        authors = Author.objects.filter(userId__in=request.data['list'])
        if not authors:
            return Response({'error': 'Author Not Found'}, status=200)
        data_list = []
        for author in authors:
            data_list.append(FindAuthorAuthorSerializer(author).data)
        return Response(data_list, status=200)
# =============================================================
class FindAuthorByFamilyViewSet(APIView):
    permission_classes = [AllowAny,]
    def post(self, request):
        if not request.data['last_name']:
            return Response({'error': 'last_name is required'}, status=404)
        firstName = get_user_model().objects.filter(first_name__contains=request.data['last_name'])
        lastName  = get_user_model().objects.filter(last_name__contains=request.data['last_name'])
        users = firstName | lastName
        if not users:
            return Response({'error': 'Author By This Name Or Family Not Found'}, status=404)
        usersId = []
        for user in users:
            usersId.append(user.id)
        authors = Author.objects.filter(userId__in=usersId).filter(status=True)
        if not authors:
            return Response({'error': 'Author By This Name Or Family Not Found'}, status=404)
        data_list = []
        for author in authors:
            data_list.append(AuthorSerializer(author).data)
        return Response(data_list, status=200)
# =============================================================
# authors profile details
class ProfileCountViewSet(APIView):
    permission_classes = [AllowAny,]
    def post(self, request):
        if not request.data:
            return Response({'error': 'authorId is required'}, status=403)
        comment = Comment.objects.filter(authorId=request.data['authorId'])
        if not comment:
            return Response({'stars': 0,'count': 0,'calls': 0}, status=200)
        stars   = comment.aggregate(Sum('stars'))['stars__sum'] / comment.count()
        calls   = CallLog.objects.filter(authorId=request.data['authorId']).count()
        return Response(
            {
                'stars': math.ceil(stars),
                'count': comment.count(),
                'calls': calls
            }
            , status=200
        )
# =============================================================
# authors comments
class CommentViewSet(ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    # lookup_field = "userId"
    permission_classes = [IsUserIdOrReadOnly]

    def get_queryset(self):
        queryset = Comment.objects.all()
        authorId = self.request.query_params.get('authorId')
        if authorId is not None:
            queryset = queryset.filter(authorId=authorId)
        
        userId = self.request.query_params.get('userId')
        if userId is not None:
            queryset = queryset.filter(userId=userId)

        return queryset
# users register shift visit using author
class UserRegisterShiftUsingAuthorViewSet(ModelViewSet):
    queryset = AuthorVisit.objects.order_by('-id')
    serializer_class = VisitSerializer
    permission_classes = [IsUserIdOrReadOnly]

    def get_queryset(self):
        queryset = AuthorVisit.objects.filter(userId=self.request.user.id)
        active = self.request.query_params.get('active')

        if active is not None:
            queryset = queryset.filter(active=True)
        
        return queryset
# =============================================================
# author view shifts
class AuthorShiftListViewSet(ModelViewSet):
    queryset            = AuthorVisit.objects.order_by('-id')
    serializer_class    = AuthorVisitListSerializer
    permission_classes  = [IsUserIdOrReadOnly]

    def get_queryset(self):
        queryset = AuthorVisit.objects.order_by('-id')
        authorId = self.request.query_params.get('authorId')
        myDate   = self.request.query_params.get('myDate')
        active   = self.request.query_params.get('active')

        if authorId is not None:
            queryset    = queryset.filter(AuthorId=authorId)
        
        if myDate is not None:
            start_week  = datetime.date.today()
            end_week    = start_week + datetime.timedelta(int(myDate))
            queryset    = queryset.filter(AuthorId=authorId).filter(visitTime__range=[start_week, end_week])

        if active is not None:
            queryset    = queryset.filter(active=True)

        return queryset
# =============================================================
# author view shifts
class AuthorShiftViewSet(ModelViewSet):
    queryset = AuthorVisit.objects.order_by('-id')
    serializer_class = AuthorVisitSerializer
    permission_classes = [IsAuthorUserIdOrReadOnly]

    def get_queryset(self):
        queryset = AuthorVisit.objects.filter(AuthorUserId=self.request.user.id)
        active   = self.request.query_params.get('active')
        if active is not None:
            start_week   = datetime.date.today()
            end_week     = start_week + datetime.timedelta(365)
            queryset = queryset.filter(active=active).filter(visitTime__range=[start_week, end_week])

        return queryset
# =============================================================
# authors create exam
class CreateExamViewSet(ModelViewSet):
    queryset = CreateExam.objects.all()
    serializer_class = CreateExamSerializer
    permission_classes = [IsUserIdOrReadOnly]

    def get_queryset(self):
        queryset = CreateExam.objects.exclude(status='d').order_by('-id')
        authorId = self.request.query_params.get('authorId')
        slug     = self.request.query_params.get('slug')
        if authorId is not None:
            queryset = queryset.filter(authorId=authorId)

        if slug is not None:
            queryset = queryset.filter(slug=slug)

        return queryset
# =============================================================
# authors exam questions
class QuestionsExamViewSet(ModelViewSet):
    queryset = QuestionsExam.objects.order_by('-id')
    serializer_class = QuestionsExamSerializer
    permission_classes = [IsUserIdOrReadOnly]
    pagination_class = LargeResultsSetPagination

    def get_queryset(self):
        queryset   = QuestionsExam.objects.order_by('-id')
        examId = self.request.query_params.get('examId')

        if examId is not None:
            queryset = queryset.filter(examId=examId)

        return queryset
# =============================================================
# users visit for exams
class CreateVisitExamViewSet(ModelViewSet):
    queryset = VisitExam.objects.order_by('-id')
    serializer_class = CreateVisitExamSerializer
    # permission_classes = [IsUserIdOrReadOnly]

    def get_queryset(self):
        queryset = VisitExam.objects.filter(userId=self.request.user.id)
        examId   = self.request.query_params.get('examId')

        if examId is not None:
            queryset = queryset.filter(examId=examId)
        
        return queryset
# =============================================================
# users visit for exams
class VisitExamViewSet(ModelViewSet):
    queryset = VisitExam.objects.order_by('-id')
    serializer_class = VisitExamSerializer
    permission_classes = [IsUserIdOrReadOnly]

    def get_queryset(self):
        queryset = VisitExam.objects.filter(userId=self.request.user.id)
        examId   = self.request.query_params.get('examId')

        if examId is not None:
            queryset = queryset.filter(examId=examId)
        
        return queryset
# =============================================================
class AnswerQuestionsViewSet(APIView):
    permission_classes = [IsUserIdOrReadOnly]

    def post(self, request):
        queryset = AnswerVisitedExam.objects.filter(userId=self.request.user.id)
        try:
            examId = request.data['examId']
            queryset = queryset.filter(examId=examId)

            data_list = []
            for query in queryset:
                data_list.append(CreateAnswerVisitedExamSerializer(query).data)
            return Response(data_list, status=200)
        except:  
            return Response({'error': 'not found'}, status=404)
# =============================================================
# users answer to questions for exams
class AnswerVisitedExamViewSet(APIView):
    permission_classes = [IsUserIdOrReadOnly]

    def post(self, request):
        if not request.data['userId']:
            return Response({'error': 'userId is required'}, status=404)
        if not request.data['examId']:
            return Response({'error': 'examId is required'}, status=404)
        if not request.data['answer']:
            return Response({'error': 'answer is required'}, status=404)
        try:
            data = []
            for answer in request.data['answer']:
                if request.data['answer'][answer]:
                    setData = {
                        'userId': request.data['userId'],
                        'examId': request.data['examId'],
                        'questionId': int(answer),
                        'answer': request.data['answer'][answer]
                    }
                    print(setData)
                    answerQuestion = CreateAnswerVisitedExamSerializer(data=setData)
                    if(answerQuestion.is_valid()):
                        answerQuestion.save()
                        data.append(answerQuestion.data)
            return Response({"data": data}, status=200)
        except:
            return Response({"error": "author by this number or last_name not found"}, status=404)
# =============================================================
# users exams visited for showed author
class UserExamForAuthorViewSet(ModelViewSet):
    queryset = VisitExam.objects.order_by('-id')
    serializer_class = UserVisitExamForAuthorSerializer
    permission_classes = [IsUserIdOrReadOnly]

    def get_queryset(self):
        queryset = VisitExam.objects.filter(active=True)
        authorId = self.request.query_params.get('authorId')

        if authorId is not None:
            authorQuestions = CreateExam.objects.exclude(status='d').filter(authorId=authorId)
            idList = []
            for authorQuestion in authorQuestions:
                idList.append(authorQuestion.id)
            queryset = queryset.filter(examId__in=idList)
        
        return queryset
        queryset = VisitExam.objects.order_by('-id')

        userId   = self.request.query_params.get('userId')
        examId   = self.request.query_params.get('examId')

        if examId is not None:
            queryset = queryset.filter(examId=examId)
        
        if userId is not None:
            queryset = queryset.filter(userId=userId)
        
        return queryset
# =============================================================
class AnswerQuestionsViewSetNew(APIView):
    permission_classes = [IsUserIdOrReadOnly]

    def post(self, request):
        queryset = AnswerVisitedExam.objects.filter(userId=request.data['userId'])
        try:
            examId = request.data['examId']
            queryset = queryset.filter(examId=examId)

            data_list = []
            for query in queryset:
                data_list.append(CreateAnswerVisitedExamSerializer(query).data)
            return Response(data_list, status=200)
        except:  
            return Response({'error': 'not found'}, status=404)
# =============================================================
class AnswerVisitedExamViewSetNew(APIView):
    permission_classes = [IsUserIdOrReadOnly]

    def post(self, request):
        try:
            try:
                queryset = VisitExam.objects.filter(userId=self.request.user.id).filter(examId=request.data['examId']).filter(active=True)
                if queryset.count():

                    visit_exam  = CreateVisitExamSerializer(queryset.get())

                    setData = {
                        'userId':       self.request.user.id,
                        'examId':       visit_exam.data['examId'],
                        'questionId':   request.data['questionId'],
                        'answer':       request.data['answer']
                    }
                    answerQuestion = CreateAnswerVisitedExamSerializer(data=setData)
                    if(answerQuestion.is_valid()):
                        answerQuestion.save()
                        return Response({"data": 'successfully'}, status=200)
                    return Response({"data": "problem in inserted"}, status=404)
                return Response({"error": "exam not found"}, status=404)
            except:
                return Response({"error": "author by this number or last_name not found"}, status=404)
        
        except:
            return Response({'error': 'examId and questionId and answer is required'}, status=404)
# =============================================================
class AuthorAnswerToVisitedExamViewSetNew(APIView):
    permission_classes = [IsUserIdOrReadOnly]

    def post(self, request):
        try:
            try:
                queryset = VisitExam.objects.filter(userId=request.data['userId']).filter(examId=request.data['examId']).filter(active=True)
                if queryset.count():
                    if queryset.get().authorAnswer is None:

                        setData = {
                            'authorAnswer': request.data['answer']
                        }

                        visit_exam  = CreateVisitExamSerializer(queryset.get(), setData)
                        if visit_exam.is_valid():
                            visit_exam.save()
                            return Response({"data": 'successfully'}, status=200)
                        return Response(visit_exam.errors, status=404)
                    
                    return Response({"data": "is answered"}, status=200)
                return Response({"error": "query not found"}, status=404)
            except:
                return Response({"error": "answer not found"}, status=404)
        except:
            return Response({'error': 'examId and questionId and answer is required'}, status=404)
# =============================================================
class SendMessageViewSet(APIView):
    def post(self, request):
        try:
            number  = get_user_model().objects.get(id=request.data['userId']).username
            number  = "0"+number
        except:
            return Response({"error": "userId is required"}, status=404)
        try:
            args    = request.data['arg']
        except:
            args    = ''

        try:
            msgId   = request.data['bodyId']
        except:
            return Response({"error": "bodyId is required"}, status=404)

        try:
            msg = '''curl -X POST https://console.melipayamak.com/api/send/shared/7cf1b880b4a94b6391298ca0a23b2bae -H 'Content-Type: application/json' -d '{"bodyId": '''+msgId+''', "to": '''+'"'+number+'"'+''' ,"args": ['''+'"'+args+'"'+'''] }' '''
            os.system(msg)
            return Response({"data": "is sended"}, status=200)
        except:
            return Response({"error": "internal server error"}, status=404)
        