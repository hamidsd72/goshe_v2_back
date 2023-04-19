from rest_framework import serializers
from .models import Category ,Notify ,Transaction ,Message  ,Follower ,Author ,Comment, Document, AuthorVisit, CreateExam ,QuestionsExam ,VisitExam ,AnswerVisitedExam
from django.contrib.auth import get_user_model

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        exclude = ("status",)

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Document
        fields = "__all__"

class NotifySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notify
        fields = "__all__"

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Transaction
        fields = ("id","amount","link","authorLink","userId","jpublish")
        
class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Transaction
        exclude = ("created_at",)

class UserAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["username","first_name","last_name","id","avatar"]

class HeadMessageSerializer(serializers.ModelSerializer):
    userId = UserAuthorSerializer()
    class Meta:
        model  = Message
        fields = ['id','userId','type','sendTo','created_at','content','attach']

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Message
        fields = ['id','userId','type','sendTo','created_at','content','attach','status','amount'] 

class FollowerSerializer(serializers.ModelSerializer):
    followId = UserAuthorSerializer()
    class Meta: 
        model  = Follower
        fields = ('userId','followId','requestUser','jpublish')

class CreateFollowerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Follower
        fields = "__all__"

class AuthorSerializer(serializers.ModelSerializer):
    userId = UserAuthorSerializer()
    class Meta:
        model  = Author
        exclude = ("updated_at","status")

class AdminAuthorSerializer(serializers.ModelSerializer):
    userId = UserAuthorSerializer()
    class Meta:
        model  = Author
        exclude = ("updated_at",)

class AdminEditAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Author
        exclude = ("updated_at",)

class CreateAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Author
        exclude = ("updated_at","status")

class FindAuthorAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Author
        fields = ("id","userId","services","oneDay","twoDay","treeDay","fourDay","fiveDay","sixDay","sevenDay","visit_type")

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Comment
        exclude = ("updated_at",)

class CreateExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreateExam
        fields = "__all__"

class QuestionsExamSerializer(serializers.ModelSerializer):
    # examId = CreateExamSerializer()
    class Meta:
        model = QuestionsExam
        fields = "__all__"

class CreateVisitExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitExam
        fields = "__all__"

class VisitExamSerializer(serializers.ModelSerializer):
    examId = CreateExamSerializer()
    class Meta:
        model = VisitExam
        fields = "__all__"

class UserVisitExamForAuthorSerializer(serializers.ModelSerializer):
    userId = UserAuthorSerializer()
    examId = CreateExamSerializer()
    class Meta:
        model = VisitExam
        fields = "__all__"

class PayedExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitExam
        fields = "__all__"

class CreateAnswerVisitedExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerVisitedExam
        fields = "__all__"

class VisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorVisit
        fields = ["AuthorId","AuthorUserId","userId","number","visitTime","autoDial","jpublish"]

class AuthorVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorVisit
        fields = ["id","userId","visitTime","autoDial","active","jpublish"]

class AuthorVisitListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorVisit
        fields = ["visitTime","active","jpublish"]

