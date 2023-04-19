# Generated by Django 3.2.7 on 2021-11-26 14:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Blog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('d', 'پیش نویس'), ('p', 'منتشر شده'), ('e', 'ویرایش شده')], default='d', max_length=1, verbose_name='وضعیت')),
                ('subject', models.CharField(max_length=250, verbose_name='عنوان')),
                ('content', models.TextField(max_length=2500, verbose_name='محتوا')),
                ('baner', models.ImageField(upload_to='blog', verbose_name='بنر')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('AuthorId', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='authorId', to='api.author', verbose_name='نویسنده')),
                ('category', models.ManyToManyField(to='api.Category', verbose_name='دسته بندی')),
            ],
        ),
    ]
