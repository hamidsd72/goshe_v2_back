from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '__first__'),
    ]
    operations = [
        migrations.CreateModel(
            name='SettlementBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_id', models.UUIDField(unique=True)),
                ('bank_reference', models.CharField(max_length=120, unique=True)),
                ('payload_hash', models.CharField(max_length=64)),
                ('paid_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('confirmed_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name='confirmed_settlement_batches', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='SettlementPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount_toman', models.PositiveIntegerField()),
                ('iban', models.CharField(max_length=26)),
                ('first_name', models.CharField(max_length=150)),
                ('last_name', models.CharField(max_length=150)),
                ('balance_before', models.BigIntegerField()),
                ('balance_after', models.BigIntegerField()),
                ('reason', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name='payments', to='consultant_accounting.settlementbatch')),
                ('consultant', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name='settlement_payments', to=settings.AUTH_USER_MODEL)),
                ('transaction', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,
                    related_name='settlement_document', to='api.transaction')),
                ('reverses', models.OneToOneField(blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT, related_name='reversal',
                    to='consultant_accounting.settlementpayment')),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(fields=('batch', 'consultant'), name='unique_batch_consultant'),
                    models.CheckConstraint(check=models.Q(amount_toman__gt=0), name='settlement_positive_amount'),
                ],
            },
        ),
    ]
