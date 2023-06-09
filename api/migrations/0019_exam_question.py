# Generated by Django 3.2.7 on 2022-02-23 13:27

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0018_transaction_authorlink'),
    ]

    operations = [
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('d', 'پیش نویس'), ('p', 'منتشر شده'), ('e', 'ویرایش شده')], default='d', max_length=1, verbose_name='وضعیت')),
                ('slug', models.SlugField(max_length=100, null=True, unique=True, verbose_name='اسلاگ')),
                ('question', models.CharField(max_length=250, verbose_name='سوال')),
                ('type', models.BooleanField(default=True, verbose_name='چهارگزینه ای')),
                ('optionA', models.CharField(max_length=250, null=True, verbose_name='الف')),
                ('optionB', models.CharField(max_length=250, null=True, verbose_name='ب')),
                ('optionC', models.CharField(max_length=250, null=True, verbose_name='ج')),
                ('optionD', models.CharField(max_length=250, null=True, verbose_name='د')),
                ('amount', models.IntegerField(default=0, verbose_name='قیمت')),
                ('baner', models.ImageField(null=True, upload_to='question', verbose_name='بنر')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('AuthorId', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='authorQuestion', to='api.author', verbose_name='مشاور')),
            ],
        ),
        migrations.CreateModel(
            name='Exam',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answer', models.CharField(max_length=250, null=True, verbose_name='حواب')),
                ('active', models.BooleanField(default=False, verbose_name='پرداخت شده')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('question', models.ManyToManyField(to='api.Question', verbose_name='سوال')),
                ('userId', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='userExam', to=settings.AUTH_USER_MODEL, verbose_name='کاربر')),
            ],
        ),
    ]
