# Generated by Django 3.2.7 on 2021-12-10 00:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_author_shaba'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='status',
            field=models.BooleanField(default=False, max_length=1, verbose_name='تایید'),
        ),
        migrations.AlterField(
            model_name='notify',
            name='content',
            field=models.TextField(max_length=2500, null=True, verbose_name='محتوا'),
        ),
    ]
