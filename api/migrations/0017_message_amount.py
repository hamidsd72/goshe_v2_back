# Generated by Django 3.2.7 on 2021-12-30 03:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0016_alter_message_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='amount',
            field=models.IntegerField(null=True, verbose_name='قیمت پیام'),
        ),
    ]
