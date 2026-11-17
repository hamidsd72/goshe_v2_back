from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from .models import Author, AuthorVisit, ReservationCredit
from . import reservation_services as services


class BookingInput(serializers.Serializer):
    AuthorId = serializers.IntegerField(min_value=1)
    number = serializers.CharField(max_length=10)
    visitTime = serializers.DateTimeField(default_timezone=services.TEHRAN)
    duration = serializers.ChoiceField(choices=services.DURATIONS)
    request_key = serializers.UUIDField()
    quoted_amount_rial = serializers.IntegerField(min_value=1)


class ReservationSerializer(serializers.ModelSerializer):
    AuthorId = serializers.IntegerField(source='visit.AuthorId_id', read_only=True)
    userId = serializers.IntegerField(source='payer_id', read_only=True)
    number = serializers.CharField(source='visit.number', read_only=True)
    visitTime = serializers.DateTimeField(source='visit.visitTime', default_timezone=services.TEHRAN, read_only=True)
    jpublish = serializers.CharField(source='visit.jpublish', read_only=True)
    active = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = ReservationCredit
        fields = ['id', 'AuthorId', 'userId', 'number', 'consultant_number', 'visitTime', 'jpublish',
                  'duration', 'ends_at', 'rate_rial', 'amount_rial', 'refunded_rial', 'status', 'active', 'can_cancel', 'request_key']
        read_only_fields = fields

    def get_active(self, obj):
        return obj.status in services.BLOCKING

    def get_can_cancel(self, obj):
        return obj.status == 'confirmed' and obj.visit.visitTime > timezone.now()


class UserRegisterShiftUsingAuthorViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    queryset = ReservationCredit.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(payer=self.request.user).select_related('visit').order_by('-id')

    def create(self, request):
        data = BookingInput(data=request.data)
        data.is_valid(raise_exception=True)
        args = data.validated_data
        get_object_or_404(Author, pk=args['AuthorId'])
        credit = services.book(request.user, args['AuthorId'], args['number'], args['visitTime'], args['duration'], args['request_key'], args['quoted_amount_rial'])
        return Response(self.get_serializer(credit).data, status=status.HTTP_201_CREATED)


class AuthorShiftViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    queryset = ReservationCredit.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(consultant=self.request.user).select_related('visit').order_by('visit__visitTime')

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        credit = services.cancel(self.get_object().pk, request.user)
        return Response(self.get_serializer(credit).data)


class AuthorShiftListViewSet(GenericViewSet):
    queryset = AuthorVisit.objects.none()
    serializer_class = serializers.Serializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        try:
            author_id = int(request.query_params.get('authorId', ''))
            duration = int(request.query_params.get('duration', 10))
        except (TypeError, ValueError):
            raise serializers.ValidationError('مشاور یا مدت معتبر نیست.')
        if duration not in services.DURATIONS:
            raise serializers.ValidationError('مدت معتبر نیست.')
        author = get_object_or_404(Author, pk=author_id, status=True, visit_type__in=['c', 'b'])
        if not author.userId_id or not author.userId.is_active or author.call_price <= 0:
            raise serializers.ValidationError('مشاور فعال نیست.')
        today = timezone.localtime(timezone.now(), services.TEHRAN).date()
        slots = []
        # Load occupied intervals once; availability is advisory, POST rechecks under locks.
        occupied = list(ReservationCredit.objects.filter(status__in=services.BLOCKING,
            ends_at__gt=timezone.now()).filter(
                services.Q(consultant_id__in=[author.userId_id, request.user.pk]) |
                services.Q(payer_id__in=[author.userId_id, request.user.pk])
            ).values_list('visit__visitTime', 'ends_at'))
        legacy = AuthorVisit.objects.filter(credit__isnull=True, AuthorUserId_id=author.userId_id,
            visitTime__gte=timezone.now()).values_list('visitTime', flat=True)
        occupied.extend((t, t + timedelta(minutes=60)) for t in legacy)
        for offset in range(1, 15):
            interval = services.work_interval(author, today + timedelta(days=offset))
            if not interval:
                continue
            start, close = interval
            start += timedelta(minutes=(-start.minute) % 10)
            while start + timedelta(minutes=duration) <= close:
                end = start + timedelta(minutes=duration)
                if not any(a < end and b > start for a, b in occupied):
                    slots.append({'start': start.isoformat(), 'end': end.isoformat()})
                start += timedelta(minutes=10)
        return Response({'slots': slots, 'duration': duration, 'rate_rial': author.call_price * 10,
            'amount_rial': author.call_price * 10 * duration, 'consultant_number': author.userId.username,
            'timezone': 'Asia/Tehran'})
