from api.models import ( Follower, Message )
from api.serializers import ( FollowerSerializer )
from api.permissions import IsUserIdOrReadOnly
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db.models import Count

class MediumResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000

class FollowerViewSet(APIView):
    permission_classes  = [IsUserIdOrReadOnly]

    def get(self, request):
        paginator = MediumResultsSetPagination()
        
        unread_message  = Message.objects.values('userId').annotate(total_items=Count('id')).filter(status=False).filter(sendTo=self.request.user.id).filter(userId__gt=0)
        ids_list        = unread_message.values_list('userId', flat=True)
        queryset        = []
        if unread_message.count():
            queryset    = Follower.objects.filter(followId__in=ids_list).filter(userId=self.request.user.id).filter(requestUser__gt=0)

        new_messages    = []
        added_items     = []
        if queryset:
            for item in queryset:
                data    = FollowerSerializer(item).data

                if data['followId']['id'] not in added_items:
                    added_items.append(data['followId']['id'])

                    data['count']   = 0
                    for l in unread_message:
                        if l['userId'] == data['followId']['id']:
                            data['count']   = l['total_items']
                            
                    new_messages.append(data)

        if unread_message.count():
            followers   = paginator.paginate_queryset( Follower.objects.exclude(followId__in=ids_list).filter(userId=self.request.user.id).filter(requestUser__gt=0), request)
        else:
            followers   = paginator.paginate_queryset( Follower.objects.filter(userId=self.request.user.id).filter(requestUser__gt=0), request)

        followers_list  = FollowerSerializer(followers, many=True)

        return Response({"new_messages": new_messages, "followers_list": paginator.get_paginated_response(followers_list.data).data}, status=200)
    