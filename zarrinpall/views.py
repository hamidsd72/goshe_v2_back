from rest_framework.response import Response
from rest_framework.views import APIView
from api.models import Transaction
from django.contrib.auth import get_user_model
from account.serializers import UserAmountSerializer
from api.serializers import PaymentTransactionSerializer
from account.serializers import MyUserSerializer, UserAmountSerializer
from rest_framework.permissions import AllowAny
from django.shortcuts import render, redirect

import requests
import json

MERCHANT        = 'a8b6eb2d-a160-4519-8861-89f754928616'
ZP_API_REQUEST  = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZP_API_STARTPAY = "http://www.zarinpal.com/pg/StartPay/"
ZP_API_VERIFY   = "https://api.zarinpal.com/pg/v4/payment/verify.json"
description     = "توضیحات مربوط به تراکنش را در این قسمت وارد کنید"
CallbackURL     = 'http://doctor.gosheshenava.com/callbackb/'

# parspal
BaseUrl         = "http://doctor.gosheshenava.com"
ReturnUrl       = "http://doctor.gosheshenava.com:8000/gateway/parspal/verify/"
# ReturnUrl       = "http://doctor.gosheshenava.com/callback/"
Currency        = "IRR"
ApiKey          = "a3dfa5c2a3e0450ca3bac5aa6bd60e21"
PaymentCreate   = "https://api.parspal.com/v1/payment/request"
VerifyUrl       = "https://api.parspal.com/v1/payment/verify"

class payment(APIView):
    def get(self, request):
        try:
            transaction = Transaction.objects.get(id=self.request.query_params.get('tId'))
        except:
            return Response({'errorMessage': 'تراکنش یافت نشد'}, status=404)
        amount      = transaction.amount 
        if amount < 100000:
            return Response({'errorMessage': 'مبلغ کمتر از ده هزار تومان است'}, status=404)
        print('CallbackURL : {0}'.format(CallbackURL))
        req_data = {
            "merchant_id": MERCHANT,
            "amount": amount,
            "callback_url": CallbackURL,
            "description": description,
            "metadata": {"mobile": str(transaction.userId)}
        }
        req_header = {
            "accept": "application/json",
            "content-type": "application/json'"
        }
        req = requests.post(
                url=ZP_API_REQUEST,
                data=json.dumps(req_data),
                headers=req_header
            )
        authority = req.json()['data']['authority']
        if len(req.json()['errors']) == 0:
            updatetransactionserializer = PaymentTransactionSerializer(transaction,data={"type": "b", "idPay_id": authority, "link": ZP_API_STARTPAY+authority})
            if updatetransactionserializer.is_valid():
                updatetransactionserializer.save()
                return Response({'link': updatetransactionserializer.data['link']}, status=200)
            return Response({'link': updatetransactionserializer.errors}, status=404)
        else:
            e_code = req.json()['errors']['code']
            e_message = req.json()['errors']['message']
            return Response({'errorCode': e_code, 'errorMessage': e_message}, status=404)

class verify(APIView):
    def get(self, request):
        if self.request.query_params.get('Status') == 'OK':
            t_authority = self.request.query_params.get('Authority')
            try:
                transaction = Transaction.objects.get(idPay_id=t_authority)
            except:
                return Response({'errorMessage': 'تراکنش یافت نشد'}, status=404)
            amount      = transaction.amount * 10
            req_header = {
                "accept": "application/json",
                "content-type": "application/json'"
            }
            req_data = {
                "merchant_id": MERCHANT,
                "amount": amount,
                "authority": t_authority
            }
            req = requests.post(url=ZP_API_VERIFY, data=json.dumps(req_data), headers=req_header)
            if len(req.json()['errors']) == 0:
                t_status = req.json()['data']['code']
                if t_status == 100:
                    params = {
                        "type": "s",
                        "status": t_status,
                        "track_id": str(req.json()['data']['ref_id']),
                        "card_no": req.json()["data"]["card_pan"],
                        "payment": req.json()['data']["card_hash"]
                    }
                    updatetransactionserializer = PaymentTransactionSerializer(transaction,data=params)
                    if updatetransactionserializer.is_valid():
                        updatetransactionserializer.save()

                        user = get_user_model().objects.get(id=updatetransactionserializer.data["userId"])
                        myuser = UserAmountSerializer(user)
                        amount = myuser.data["amount"] + updatetransactionserializer.data["amount"]
                        userAmountUpdate = UserAmountSerializer(user, data={"amount": amount, "username": myuser.data["username"]})
                        if userAmountUpdate.is_valid():
                            userAmountUpdate.save()
                            return Response({"authorLink": transaction.authorLink}, status=200)
                        return Response(userAmountUpdate.errors, status=404)
                    return Response(updatetransactionserializer.errors, status=404)
                elif t_status == 101:
                    return Response({'errorCode': 'transaction submitted' ,'errorMessage': req.json()['data']['message']}, status=200)
                else:
                    return Response({'errorCode': 'transaction failed status' ,'errorMessage': req.json()['data']['message']}, status=200)
            else:
                e_code = req.json()['errors']['code']
                e_message = req.json()['errors']['message']
                return Response({'errorCode': e_code,'errorMessage': e_message}, status=404)
        else:
            return Response({'errorCode': self.request.query_params.get('Status'),'errorMessage': 'transaction failed or canceled by user'}, status=404)


    
class parspalCreate(APIView):
    def post(self, request):
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

        payload = json.dumps({
            "amount": transactionserializer.data["amount"],
            # "return_url": ReturnUrl+str(request.data['order_id']),
            "return_url": ReturnUrl,
            "currency": Currency,
            "reserve_id": str(transactionserializer.data["id"]),
            "order_id": str(transactionserializer.data["id"]),
            "payer": {
                "name": "بنی هاشمی",
                "mobile": userserializer.data["username"],
                "email": "admin@mail.com"
            },
            "description": "بسته مشاوره",
            "default_psp": ""
        })

        headers = {"ApiKey": ApiKey,"Content-Type": "application/json"}
        
        try:
            response = requests.request("POST", PaymentCreate, headers=headers, data=payload)
        except:
            return Response( {"msg": "ارتباط با درگاه برقرار نشد"}, status=400)

        try:
            if response.json()["status"]=="ACCEPTED":
                if response.json()["payment_id"]:

                    updatetransactionserializer = PaymentTransactionSerializer(transaction,data={"type": "b", "idPay_id": response.json()["payment_id"], "link": response.json()["link"]})
                    if updatetransactionserializer.is_valid():
                        updatetransactionserializer.save()
                        return Response( {"link": updatetransactionserializer.data["link"] }, status=200)
                    return Response( updatetransactionserializer.errors, status=400)
                    
                return Response( {"msg": "اطلاعات بازگشتی کامل نیست تراکنش لغو شد. حداکثر تا ۲۴ ساعت دیگر مبلغ به حساب شما برگشت میشود"}, status=400)
            
            return Response({"msg": response.json()["message"]}, status=400)
        
        except:
            return Response( {"msg": "خطا"}, status=400)

class parspalCallBack(APIView):
    permission_classes = [AllowAny,]

    def post(self, request):
        try:
            transaction = Transaction.objects.get(id=request.data['order_id'])

            if int(request.data['status'])==100:
                
                payload = json.dumps({
                    "amount": transaction.amount,
                    "receipt_number": request.data['receipt_number'],
                    "currency": Currency
                })

                headers = {"ApiKey": ApiKey,"Content-Type": "application/json"}

                try:        
                    response = requests.request("POST", VerifyUrl, headers=headers, data=payload)
                except:
                    return Response( {"msg": "خظا از سامانه پرداخت"}, status=400)

                if response.json()['status']=='SUCCESSFUL':
                    params = {
                        "type": "s",
                        "status": 100,
                        "track_id": response.json()['id'],
                        "card_no": int(request.data['receipt_number']),
                        "payment": response.json()["message"]
                    }
                else:
                    params = {
                        "status": 99,
                        "card_no": int(request.data['receipt_number']),
                        "payment": response.json()["message"]
                    }

                updatetransactionserializer = PaymentTransactionSerializer(transaction,data=params)
                if updatetransactionserializer.is_valid():
                    updatetransactionserializer.save()
                    if response.json()['status']=='SUCCESSFUL':
                        user = get_user_model().objects.get(id=updatetransactionserializer.data["userId"])
                        myuser = UserAmountSerializer(user)
                        amount = myuser.data["amount"] + updatetransactionserializer.data["amount"]
                        userAmountUpdate = UserAmountSerializer(user, data={"amount": amount, "username": myuser.data["username"]})
                        if userAmountUpdate.is_valid():
                            userAmountUpdate.save()
                        # return Response( userAmountUpdate.errors, status=200)

                            return redirect(BaseUrl+transaction.authorLink)
                            # return Response( {"authorLink": transaction.authorLink}, status=200)

                # return Response( updatetransactionserializer.errors, status=400)
            return Response( {"msg": "خطا در ثبت گزارش جهت پیگیری با پشتیبانی تماس بگیرید", "data": request.data}, status=400)


        except:
            return Response({"msg": "درخواست معتبر نیست"}, status=400)
            