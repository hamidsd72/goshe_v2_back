from .models import Ticket
from .serializers import TicketSerializer , TicketSerializer2 , AdminTicketSerializer, CompletedTicketSerializer
from rest_framework.viewsets import ModelViewSet
from api.permissions import IsSuperUserOrReadOnly, IsSuperUser, IsUserIdOrReadOnly
from rest_framework.views import APIView 
from django.contrib.auth import get_user_model
import datetime
from rest_framework.response import Response
import os


class TicketViewSet(ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [IsUserIdOrReadOnly]

    def get_queryset(self):
        queryset = Ticket.objects.all()
        queryset2 = Ticket.objects.all()

        userId = self.request.query_params.get('userId')
        if userId is not None:
            queryset = queryset.filter(userId=userId)
            queryset2 = queryset2.filter(sendTo=userId)

        final = queryset | queryset2

        return final.order_by('-id')

class TicketViewSet2(ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer2
    permission_classes = [IsUserIdOrReadOnly]

    def get_queryset(self):
        queryset = Ticket.objects.all()
        queryset2 = Ticket.objects.all()

        userId = self.request.query_params.get('userId')
        if userId is not None:
            queryset = queryset.filter(userId=userId)
            queryset2 = queryset2.filter(sendTo=userId)

        final = queryset | queryset2

        return final.order_by('-id')

class AdminViewTicketViewSet(ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = AdminTicketSerializer
    permission_classes = [IsSuperUser]

    def get_queryset(self):
        queryset = Ticket.objects.filter(status=False)

        userId = self.request.query_params.get('userId')
        lastday = self.request.query_params.get('lastday')

        if userId is not None:
            queryset = queryset.filter(userId=userId)

        if lastday is not None:
            date = datetime.date.today()
            start_week = date - datetime.timedelta(int(lastday))
            end_week   = datetime.date.today()
            queryset   = queryset.filter(created_at__range=[start_week, end_week])

        return queryset.order_by('-id')

class AdminTicketViewSet(APIView):
    permission_classes = [IsSuperUser]

    def post(self, request):
        errors = []
        tickets = Ticket.objects.filter(status=False).filter(userId=request.data['userId'])
        for ticket in tickets:
            adminTicket = CompletedTicketSerializer(ticket,data={"status": True})
            if(adminTicket.is_valid()):
                adminTicket.save()
            errors.append(adminTicket.errors)
        return Response({"msg":"با موفقیت انجام شد","errors": errors}, status=200)

class SendAdminMsgToUserViewSet(APIView):
    permission_classes = [IsSuperUser,]
    def post(self, request):
        try:
            title  = '"args": [ "'+request.data['param']+'" ]'
            base   = "curl -X POST https://console.melipayamak.com/api/send/shared/1515c626310f4b529d6af64d0acedafe -H 'Content-Type: application/json' -d "
            bodyId = '{"bodyId": '+request.data['bodyId']+',"to":'
            to     = ' "'+request.data['username']+'"'+', '
            end    = title+'}'
            msg    = base+"'"+bodyId+to+end+"' "
            
            os.system(msg)
            return Response({"msg": "پیامک برای کاربر ارسال شد"}, status=200)
        except:
            return Response({"errors": "اشگال در ارسال پیام"}, status=400)
