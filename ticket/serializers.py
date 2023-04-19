from django.db.models import fields
from .models import Ticket
from rest_framework import serializers
from api.serializers import UserAuthorSerializer

class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("userId","subject","content","baner","jpublish")

class TicketSerializer2(serializers.ModelSerializer):
    userId = UserAuthorSerializer()
    class Meta:
        model = Ticket
        fields = ("userId","subject","content","baner","jpublish")

class AdminTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("id","userId","sendTo","subject","content","baner","status","jpublish")

class CompletedTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("status",)

