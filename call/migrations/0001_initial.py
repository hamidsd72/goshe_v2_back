# Generated by Django 3.2.7 on 2021-11-26 14:48

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CallLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Sitak_id', models.IntegerField(null=True, verbose_name='شماره سیتک')),
                ('type', models.CharField(default='در حال تماس', max_length=50, verbose_name='نوع تماس')),
                ('FirstCredit', models.IntegerField(null=True, verbose_name='شارژ اولیه')),
                ('call_amount', models.IntegerField(null=True, verbose_name='هزینه تماس')),
                ('AmountPerMin', models.IntegerField(null=True, verbose_name='هزینه هر دقیقه')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('authorId', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='DoctorCallId', to=settings.AUTH_USER_MODEL, verbose_name='کارمند')),
                ('userId', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='userCallLog', to=settings.AUTH_USER_MODEL, verbose_name='کاربر')),
            ],
        ),
    ]
