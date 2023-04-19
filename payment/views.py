from rest_framework.views import APIView
from rest_framework.response import Response
import requests
import json

from api.models import Transaction, CreateExam, VisitExam
from django.contrib.auth import get_user_model
from api.serializers import PaymentTransactionSerializer, PayedExamSerializer
from account.serializers import MyUserSerializer, UserAmountSerializer
from rest_framework.permissions import AllowAny

class PaymentCreateViewSet(APIView):
    def post(self, request):
        try:
            try:
                transaction = Transaction.objects.get(id=request.data['order_id']) 
            except:
                return Response({"msg": "تراکنش یافت نشد"}, status=400)
            
            try:
                transactionserializer = PaymentTransactionSerializer(transaction)
            except:
                return Response({"msg": "خطا در مدل"}, status=400)
            
            try:
                userserializer = MyUserSerializer(get_user_model().objects.get(id=transactionserializer.data["userId"]))
            except:
                return Response({"msg": "خطا در مدل ۲"}, status=400)
            
            url = "https://api.idpay.ir/v1.1/payment"

            payload = json.dumps({
                "order_id": transactionserializer.data["id"],
                "amount": transactionserializer.data["amount"],
                # "name": "قاسم رادمان",
                "phone": userserializer.data["username"],
                # "mail": "my@site.com",
                # "desc": "توضیحات پرداخت کننده",
                "callback": "http://doctor.gosheshenava.com/callback/"+str(request.data['order_id'])
            })
            headers = {
                'Content-Type': 'application/json',
                'X-API-KEY': '712993a7-1bf1-4232-8057-21cd53134225',
                'X-SANDBOX': '0'
            }
            # return Response(payload, status=200)
            try:
                response = requests.request("POST", url, headers=headers, data=payload)
            except:
                return Response({"msg": "خطا در ارتباط با درگاه"}, status=400)
            
            try:
                if response.json()["id"]:
                    updatetransactionserializer = PaymentTransactionSerializer(transaction,data={"type": "b", "idPay_id": response.json()["id"], "link": response.json()["link"]})
                    if updatetransactionserializer.is_valid():
                        updatetransactionserializer.save()
                        return Response( {"link": updatetransactionserializer.data["link"] }, status=200)
                    return Response( updatetransactionserializer.errors, status=400)
                return Response( response.json(), status=200)
            except:
                return Response({"msg": response.json()}, status=400)
            
        except:
            return Response({"msg": "مشگل ناشناخته"}, status=400)
            
class IdPayCallBack(APIView):
    permission_classes = [AllowAny,]

    def post(self, request): 
        try:
            transaction = Transaction.objects.get(id=request.data['id'])
            transactionserializer = PaymentTransactionSerializer( transaction )
        except:
            return Response( {"msg": "تراکنش یافت نشد"}, status=400)
        if transactionserializer.data["type"] == 'b':
            url = "https://api.idpay.ir/v1.1/payment/verify"
            payload = json.dumps({
                "id": transactionserializer.data["idPay_id"],
                "order_id": transactionserializer.data["id"]
            })

            headers = {
                'Content-Type': 'application/json',
                'X-API-KEY': '712993a7-1bf1-4232-8057-21cd53134225',
                'X-SANDBOX': '0'
            }
            
            try:        
                response = requests.request("POST", url, headers=headers, data=payload)
            except:
                return Response( {"msg": "خظا از سامانه پرداخت"}, status=400)

            params = {
                "type": "s",
                "status": response.json()['status'],
                "track_id": response.json()['track_id'],
                "card_no": response.json()["payment"]["card_no"],
                "payment": str( response.json()["payment"] )
            }
            updatetransactionserializer = PaymentTransactionSerializer(transaction,data=params)
            if updatetransactionserializer.is_valid():
                updatetransactionserializer.save()
                # return Response( updatetransactionserializer.data, status=200)
                user = get_user_model().objects.get(id=updatetransactionserializer.data["userId"])
                myuser = UserAmountSerializer(user)
                amount = myuser.data["amount"] + updatetransactionserializer.data["amount"]

                userAmountUpdate = UserAmountSerializer(user, data={"amount": amount, "username": myuser.data["username"]})
                if userAmountUpdate.is_valid():
                    userAmountUpdate.save()
                    return Response( {"authorLink": transaction.authorLink}, status=200)
                # return Response( userAmountUpdate.errors, status=200)
            # return Response( updatetransactionserializer.errors, status=400)
            return Response( {"msg": "خطا در ثبت گزارش جهت پیگیری با پشتیبانی تماس بگیرید"}, status=400)
        return Response( {"msg": "درخواست معتبر نیست"}, status=200)

class PaymentExamViewSet(APIView):
    def post(self, request):
        try:
            questionAmount = CreateExam.objects.get(id=request.data['examId']).amount * 10
            exam = VisitExam.objects.get(id=request.data['questionId'])
            user = get_user_model().objects.get(id=self.request.user.id)
            if user.amount >= questionAmount:
                amount = user.amount - questionAmount
                userAmount = UserAmountSerializer(user,data={"username": user.username, "amount": amount})
                if userAmount.is_valid():
                    compeletedExam = PayedExamSerializer(exam, data={"active": True})
                    if compeletedExam.is_valid():
                        compeletedExam.save()
                        userAmount.save()
                    return Response( {"amount": userAmount.data["amount"] }, status=200)
            return Response({"error": "موجودی کافی نیست"}, status=400)
        except:
            return Response({"error": "مشگل داخلی سرور"}, status=400)
 