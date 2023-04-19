from .serializers import CallLogSerializer , UpdateCallLogSerializer , NewCallLogSerializer, NumberSerializer, CallLogSerializer_v2
from api.permissions import IsSuperUserOrReadOnly, IsSuperUser
from account.serializers import MyUserSerializer, UserAmountSerializer
from api.serializers import CreateAuthorSerializer, HeadMessageSerializer
from .models import CallLog, Number
from api.models import Author, Message, Transaction
from django.contrib.auth import get_user_model
from rest_framework.viewsets import ModelViewSet
from django.db.models import Sum
import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
import requests

class CallCreateViewSet(APIView):
    def post(self, request):
        try:
            # check get userIdAuthor and userNember
            checkUserIdAuthor = request.data['userIdAuthor']
            checkUserNember   = str(request.data['userNember'])
            # check author is live else busy
            if CallLog.objects.filter(type="کد 1 در حال تماس").filter(authorId=checkUserIdAuthor).count():
                # return Response({"msg": "consultant is busy, please try later"}, status=400)
                return Response({"msg": "مشاور با شخص دیگری درحال مکالمه میباشد"}, status=400)
            # find number from myNumbers
            if  self.request.user.username != str(checkUserNember):
                if not Number.objects.filter(userId=self.request.user.id).filter(number=checkUserNember).count():
                    return Response({"msg": checkUserNember+" in list subNumber Not Found..."}, status=400)
        except:
            return Response({"msg": "'userNember' and 'userIdAuthor' is required"}, status=400)
        try:
            try:
                # first step find request user from self.request.user.id
                userId = get_user_model().objects.get(id=self.request.user.id)
            except:
                return Response({"msg": "کاربر یافت نشد"}, status=400)
            user = MyUserSerializer(userId)
            
            # get user amount
            amount = UserAmountSerializer(userId).data['amount']
            try:
                # find author for call request using authorId
                authorserializer = CreateAuthorSerializer(Author.objects.get(userId=request.data['userIdAuthor']))
            except:
                return Response({"msg": "مشاور یافت نشد"}, status=400)
            # check inventory amount for call
            if amount < (authorserializer.data['call_price'] * 10):
                return Response({"msg": "موجودی کافی نیست"}, status=400)
            # check for request user != author user
            if user.data['id'] == authorserializer.data['userId']:
                return Response({"msg": "کاربر و مشاور یکی هستند"}, status=400)
            # find user this author for find username using create call
            authorUsername = get_user_model().objects.get(id=authorserializer.data['userId']).username
            # update to zero amount user request
            updateToZeroAmount = UserAmountSerializer(userId,data={"amount": 0,"username": userId.username})
            if(updateToZeroAmount.is_valid()):
                updateToZeroAmount.save()
                # step 1: set params to create call log 
                params = {
                    "userId": self.request.user.id,
                    "authorId": authorserializer.data['userId'],
                    "FirstCredit": amount,
                    "AmountPerMin": authorserializer.data['call_price']*10
                    }
                # step 1.1 : create call log
                calLog = NewCallLogSerializer(data=params)
                if(calLog.is_valid()):
                    calLog.save()
                    # step 2 : set params to send request to "abdolmaleky api"
                    url = "http://93.118.104.154:61230/FirstAPI.php?="
                    call_id      = str(calLog.data['id'])
                    firstNum     = str(request.data['userNember'])
                    secendNum    = authorUsername
                    FirstCredit  = str(amount)
                    AmountPerMin = str(authorserializer.data['call_price']*10)
                    data={
                        "call_id": call_id,
                        "CustomerNum": "0"+firstNum,    
                        "ConsultantNum": "0"+secendNum,
                        "Credit": FirstCredit,
                        "AmountPerMin": AmountPerMin
                    }
                    files=[]
                    headers = { 'Authorization': 'Basic c2l0YWs6d3EzMXcyM2R0U3dBTUoyMzI3d1VVOVJ2OTViYzY1NEM=' }
                    # step 2.2 : send request call to "abdolmaleky api"
                    response = requests.request("POST", url, headers=headers, data=data, files=files)
                    # return Response( response.json(), status=200)
                    if response.json()['Sitak_id']:
                        # find call log for update sitak_id 
                        findCall = CallLog.objects.get(id=calLog.data['id'])
                        # update sitak_id call log 
                        updateCallLog = NewCallLogSerializer(findCall,data={"Sitak_id": response.json()['Sitak_id'],"type": (" کد "+str(response.json()['status_id'])+" در حال تماس ")})
                        if(updateCallLog.is_valid()):
                            updateCallLog.save()
                            return Response(updateCallLog.data, status=201)
                        return Response(updateCallLog.errors, status=400)
                    return Response({"msg": "نتیجه نامعلوم ,اتصال با سرور تماس برقرار نشد"}, status=400)
                # return Response(calLog.errors, status=400)
            # return Response(updateToZeroAmount.errors, status=400)
        except:
            return Response({"msg": "مشگل در ارسال اطلاعات"}, status=400)

class AdminCallCreateViewSet(APIView):
    permission_classes = [IsSuperUser]
    def post(self, request):
        url = "http://93.118.104.154:61230/FirstAPI.php?="
        call_id      = "1"
        firstNum     = request.data["myMobile"]
        secendNum    = request.data["username"]
        FirstCredit  = "10000"
        AmountPerMin = "10"
        data={
            "call_id": call_id,
            "CustomerNum": "0"+firstNum,    
            "ConsultantNum": "0"+secendNum,
            "Credit": FirstCredit,
            "AmountPerMin": AmountPerMin
        }
        files=[]
        headers = { 'Authorization': 'Basic c2l0YWs6d3EzMXcyM2R0U3dBTUoyMzI3d1VVOVJ2OTViYzY1NEM=' }
        response = requests.request("POST", url, headers=headers, data=data, files=files)
        if response.json()['Sitak_id']:
            return Response(response.json(), status=200)
        return Response({"msg": "نتیجه نامعلوم ,اتصال با سرور تماس برقرار نشد"}, status=400)

class UpdateCallCreateViewSet(APIView):
    permission_classes = [IsSuperUserOrReadOnly,]
    def post(self, request):
        try:
            try:
                findCall = CallLog.objects.get(Sitak_id=request.data['Sitak_id'])
            except:
                return Response({"error": "تماس یافت نشد"}, status=200)
                
            params = {
                "type": 'Customer : '+request.data['Customer_Call_Detail']+' , '+' Consultant : '+request.data['Consultant_Call_Detail'],
                "call_amount": int( request.data['call_amount'] )
            }

            updateCallLog = UpdateCallLogSerializer(findCall,data=params)
            if(updateCallLog.is_valid()):
                updateCallLog.save()

                authUser    = get_user_model().objects.get(id=updateCallLog.data["userId"])
                amountUpdate = UserAmountSerializer(authUser, data={"username": authUser.username,"amount": (authUser.amount + int(request.data['LastCredit']) ) })
                if(amountUpdate.is_valid()):
                    amountUpdate.save()
                    return Response(amountUpdate.data, status=200)
                return Response(amountUpdate.errors, status=200)

            return Response(updateCallLog.errors, status=400)
        except:
            return Response({"error": "مشگل در ارتباط"}, status=400)

class CallLogViewSet(ModelViewSet):
    queryset = CallLog.objects.all()
    serializer_class = CallLogSerializer
    permission_classes = [IsSuperUserOrReadOnly]
    def get_queryset(self):
        return CallLog.objects.filter(userId=self.request.user.id).order_by('-id')

class CallLogViewSet_v2(ModelViewSet):
    queryset = CallLog.objects.all()
    serializer_class = CallLogSerializer_v2
    permission_classes = [IsSuperUserOrReadOnly]
    def get_queryset(self):

        query   = Q(userId  = self.request.user.id )
        query.add(Q(authorId= self.request.user.id), Q.OR)

        return CallLog.objects.filter(query).order_by('-id')

class FlashCallLogViewSet(APIView):
    permission_classes = [IsSuperUserOrReadOnly]
    def post(self, request):
        queryset = CallLog.objects.filter(type="کد 1 در حال تماس")
        if queryset.count() > 0:
            for q in queryset:
                complete = CallLogSerializer(q,data={"type": "admin edit"})
                if(complete.is_valid()):
                    complete.save()
        return Response({'completedMessage': queryset.count()}, status=200)

class NumbersViewSet(ModelViewSet):
    queryset = Number.objects.all()
    serializer_class = NumberSerializer
    def get_queryset(self):
        return Number.objects.filter(userId=self.request.user.id).order_by('-id')

class CallAndMessageLogView(APIView):
    def get(self, request):
        myCalls   = CallLog.objects.filter(authorId=self.request.user.id).aggregate(Sum('call_amount'))
        myMessage = Message.objects.filter(sendTo=self.request.user.id).aggregate(Sum('amount'))
        myRevenue = Transaction.objects.filter(userId=self.request.user.id).filter(type='w').aggregate(Sum('amount'))
        return Response({"myCalls": myCalls["call_amount__sum"],"myMessage": myMessage["amount__sum"],"myRevenue": myRevenue["amount__sum"]}, status=200)

class AdminCallAndMessageLogView(APIView):
    permission_classes = [IsSuperUser]
    def post(self, request):
        date  = datetime.date.today()
        today = date - datetime.timedelta(1)
        week  = date - datetime.timedelta(7)
        month = date - datetime.timedelta(30)
        year  = date - datetime.timedelta(365)
        try:
            callQuery        = CallLog.objects.filter(authorId=request.data['userId'])
            messageQuery     = Message.objects.filter(sendTo=request.data['userId'])
            TransactionQuery = Transaction.objects.filter(userId=request.data['userId'])

            call    = callQuery.aggregate(Sum('call_amount'))["call_amount__sum"]
            message = messageQuery.aggregate(Sum('amount'))["amount__sum"]
            revenue = TransactionQuery.filter(type='w').aggregate(Sum('amount'))["amount__sum"]
            buy     = TransactionQuery.filter(type='s').aggregate(Sum('amount'))["amount__sum"]
            gift    = TransactionQuery.filter(type='g').aggregate(Sum('amount'))["amount__sum"]

            today_call   = callQuery.filter(created_at__range=[today, date]).aggregate(Sum('call_amount'))["call_amount__sum"]
            weekly_call  = callQuery.filter(created_at__range=[week, date]).aggregate(Sum('call_amount'))["call_amount__sum"]
            monthly_call = callQuery.filter(created_at__range=[month, date]).aggregate(Sum('call_amount'))["call_amount__sum"]
            yearly_call  = callQuery.filter(created_at__range=[year, date]).aggregate(Sum('call_amount'))["call_amount__sum"]
            list_call         = {"today": today_call, "week": weekly_call, "month": monthly_call, "year": yearly_call}

            today_message   = messageQuery.filter(created_at__range=[today, date]).aggregate(Sum('amount'))["amount__sum"]
            weekly_message  = messageQuery.filter(created_at__range=[week, date]).aggregate(Sum('amount'))["amount__sum"]
            monthly_message = messageQuery.filter(created_at__range=[month, date]).aggregate(Sum('amount'))["amount__sum"]
            yearly_message  = messageQuery.filter(created_at__range=[year, date]).aggregate(Sum('amount'))["amount__sum"]
            list_message         = {"today": today_message, "week": weekly_message, "month": monthly_message, "year": yearly_message}

            return Response({"call": call,"message": message,"revenue": revenue,"buy": buy,"gift": gift,"list_call": list_call,"list_message": list_message}, status=200)
        except:
            callQuery        = CallLog.objects.all()
            messageQuery     = Message.objects.all()
            TransactionWQuery = Transaction.objects.filter(type='w')
            TransactionSQuery = Transaction.objects.filter(type='s')
            TransactionGQuery = Transaction.objects.filter(type='g')

            today_call   = callQuery.filter(created_at__range=[today, date]).aggregate(Sum('call_amount'))["call_amount__sum"]
            weekly_call  = callQuery.filter(created_at__range=[week, date]).aggregate(Sum('call_amount'))["call_amount__sum"]
            monthly_call = callQuery.filter(created_at__range=[month, date]).aggregate(Sum('call_amount'))["call_amount__sum"]
            yearly_call  = callQuery.filter(created_at__range=[year, date]).aggregate(Sum('call_amount'))["call_amount__sum"]
            call         = {"today": today_call, "week": weekly_call, "month": monthly_call, "year": yearly_call}

            today_message   = messageQuery.filter(created_at__range=[today, date]).aggregate(Sum('amount'))["amount__sum"]
            weekly_message  = messageQuery.filter(created_at__range=[week, date]).aggregate(Sum('amount'))["amount__sum"]
            monthly_message = messageQuery.filter(created_at__range=[month, date]).aggregate(Sum('amount'))["amount__sum"]
            yearly_message  = messageQuery.filter(created_at__range=[year, date]).aggregate(Sum('amount'))["amount__sum"]
            message         = {"today": today_message, "week": weekly_message, "month": monthly_message, "year": yearly_message}
            
            today_revenue   = TransactionWQuery.filter(created_at__range=[today, date]).aggregate(Sum('amount'))["amount__sum"]
            weekly_revenue  = TransactionWQuery.filter(created_at__range=[week, date]).aggregate(Sum('amount'))["amount__sum"]
            monthly_revenue = TransactionWQuery.filter(created_at__range=[month, date]).aggregate(Sum('amount'))["amount__sum"]
            yearly_revenue  = TransactionWQuery.filter(created_at__range=[year, date]).aggregate(Sum('amount'))["amount__sum"]
            revenue         = {"today": today_revenue, "week": weekly_revenue, "month": monthly_revenue, "year": yearly_revenue}

            today_buy   = TransactionSQuery.filter(created_at__range=[today, date]).aggregate(Sum('amount'))["amount__sum"]
            weekly_buy  = TransactionSQuery.filter(created_at__range=[week, date]).aggregate(Sum('amount'))["amount__sum"]
            monthly_buy = TransactionSQuery.filter(created_at__range=[month, date]).aggregate(Sum('amount'))["amount__sum"]
            yearly_buy  = TransactionSQuery.filter(created_at__range=[year, date]).aggregate(Sum('amount'))["amount__sum"]
            buy         = {"today": today_buy, "week": weekly_buy, "month": monthly_buy, "year": yearly_buy}

            today_gift   = TransactionGQuery.filter(created_at__range=[today, date]).aggregate(Sum('amount'))["amount__sum"]
            weekly_gift  = TransactionGQuery.filter(created_at__range=[week, date]).aggregate(Sum('amount'))["amount__sum"]
            monthly_gift = TransactionGQuery.filter(created_at__range=[month, date]).aggregate(Sum('amount'))["amount__sum"]
            yearly_gift  = TransactionGQuery.filter(created_at__range=[year, date]).aggregate(Sum('amount'))["amount__sum"]
            gift         = {"today": today_gift, "week": weekly_gift, "month": monthly_gift, "year": yearly_gift}
                        
            return Response({"call": call ,"message": message ,"revenue": revenue ,"buy": buy ,"gift": gift}, status=200)

class AdminShowUserCallView(ModelViewSet):
    serializer_class = NewCallLogSerializer
    permission_classes = [IsSuperUser]
    queryset = CallLog.objects.all()
    
    def get_queryset(self):
        queryset = CallLog.objects.all()

        userId = self.request.query_params.get('userId')
        if userId is not None:
            queryset = queryset.filter(authorId=userId).order_by('-id')
        
        return queryset

class AdminShowUserMessageView(ModelViewSet):
    serializer_class = HeadMessageSerializer
    permission_classes = [IsSuperUser]
    queryset = Message.objects.all()
    
    def get_queryset(self):
        queryset = Message.objects.all()

        userId = self.request.query_params.get('userId')
        if userId is not None:
            queryset = queryset.filter(sendTo=userId).order_by('-id')
        
        return queryset


class ActiveCallLogViewSet(ModelViewSet):
    queryset = CallLog.objects.all()
    serializer_class = CallLogSerializer
    permission_classes = [IsSuperUserOrReadOnly]
    def get_queryset(self):
        queryset = CallLog.objects.filter(type="کد 1 در حال تماس").order_by('-id')

        userId = self.request.query_params.get('userId')
        if userId is not None:
            queryset = queryset.filter(userId=userId).order_by('-id')

        authorId = self.request.query_params.get('authorId')
        if authorId is not None:
            queryset = queryset.filter(authorId=authorId).order_by('-id')
        
        return queryset
