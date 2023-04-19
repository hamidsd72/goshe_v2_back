from rest_framework import serializers
from .models import CallLog, Number

class CallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CallLog
        fields = ["id" , "type", "FirstCredit", "call_amount", "AmountPerMin", "jpublish"]

class CallLogSerializer_v2(serializers.ModelSerializer):
    class Meta:
        model  = CallLog
        fields = ["id" , "type", "FirstCredit", "call_amount", "AmountPerMin", "jpublish","userId","authorId"]

class UpdateCallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CallLog
        fields = ["id","Sitak_id","call_amount","type","userId"]

class NewCallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CallLog
        fields = "__all__"

class NumberSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Number
        fields = fields = [ "id", "userId", "number", "subject", "jpublish"]