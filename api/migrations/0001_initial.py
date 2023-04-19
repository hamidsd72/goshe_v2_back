# Generated by Django 3.2.7 on 2021-11-26 14:47

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
            name='Author',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uid', models.IntegerField(default=0, verbose_name='شماره جواز کار')),
                ('call_price', models.IntegerField(default=0, verbose_name='نرخ پیام')),
                ('msg_price', models.IntegerField(default=0, verbose_name='نرخ تماس')),
                ('status', models.BooleanField(default=False, verbose_name='وضعیت')),
                ('older', models.TextField(max_length=2500, null=True, verbose_name='سابقه')),
                ('oneDay', models.CharField(max_length=250, null=True, verbose_name='روز اول')),
                ('twoDay', models.CharField(max_length=250, null=True, verbose_name='روز دوم')),
                ('treeDay', models.CharField(max_length=250, null=True, verbose_name='روز سوم')),
                ('fourDay', models.CharField(max_length=250, null=True, verbose_name='روز چهار')),
                ('fiveDay', models.CharField(max_length=250, null=True, verbose_name='روز پنج')),
                ('sixDay', models.CharField(max_length=250, null=True, verbose_name='روز شش')),
                ('sevenDay', models.CharField(max_length=250, null=True, verbose_name='روز هفت')),
                ('visit_type', models.CharField(choices=[('m', 'message'), ('c', 'call'), ('b', 'both')], default='c', max_length=1, verbose_name='نوع ویزیت')),
                ('certificate', models.CharField(max_length=50, null=True, verbose_name='مدرک تحصیلی')),
                ('services', models.BooleanField(default=False, verbose_name='نوع سرویس')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=250, verbose_name='عنوان')),
                ('slug', models.SlugField(max_length=100, unique=True, verbose_name='اسلاگ')),
                ('baner', models.ImageField(upload_to='baner', verbose_name='بنر')),
                ('status', models.BooleanField(default=True, verbose_name='نمایش')),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.IntegerField(default=0, verbose_name='مبلغ')),
                ('type', models.CharField(choices=[('p', 'پیش فاکتور'), ('b', 'خرید'), ('w', 'بازپرداخت'), ('g', 'هدیه')], default='p', max_length=1, verbose_name='نوع')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('userId', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='userTransaction', to=settings.AUTH_USER_MODEL, verbose_name='کاربر')),
            ],
        ),
        migrations.CreateModel(
            name='Notify',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('o', 'one'), ('t', 'two'), ('r', 'tree')], default='o', max_length=1, verbose_name='نوع')),
                ('title', models.CharField(max_length=250, verbose_name='عنوان')),
                ('content', models.TextField(null=True, verbose_name='محتوا')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('userId', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='userNotify', to=settings.AUTH_USER_MODEL, verbose_name='کاربر')),
            ],
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('n', 'normal'), ('s', 'special')], default='n', max_length=1, verbose_name='نوع')),
                ('content', models.TextField(null=True, verbose_name='محتوا')),
                ('attach', models.ImageField(null=True, upload_to='files', verbose_name='فایل')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sendTo', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sendToMessage', to=settings.AUTH_USER_MODEL, verbose_name='ارسال به')),
                ('userId', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='userMessage', to=settings.AUTH_USER_MODEL, verbose_name='کاربر')),
            ],
        ),
        migrations.CreateModel(
            name='Follower',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('followId', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='userFollower', to=settings.AUTH_USER_MODEL, verbose_name='فالوور')),
                ('userId', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='userId', to=settings.AUTH_USER_MODEL, verbose_name='کاربر')),
            ],
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stars', models.IntegerField(default=3, null=True, verbose_name='سناره')),
                ('content', models.TextField(null=True, verbose_name='محتوا')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('authorId', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='AuthorDoctorId', to='api.author', verbose_name='کارمند')),
                ('userId', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='userComment', to=settings.AUTH_USER_MODEL, verbose_name='کاربر')),
            ],
        ),
        migrations.AddField(
            model_name='author',
            name='category',
            field=models.ManyToManyField(to='api.Category', verbose_name='دسته بندی'),
        ),
        migrations.AddField(
            model_name='author',
            name='userId',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='userAuthor', to=settings.AUTH_USER_MODEL, verbose_name='کاربر'),
        ),
    ]
