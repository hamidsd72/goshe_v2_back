# Generated by Django 3.2.7 on 2021-12-01 02:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_auto_20211130_2153'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='type',
            field=models.CharField(choices=[('p', 'پیش فاکتور'), ('b', 'خرید'), ('s', 'تکمیل شده'), ('w', 'بازپرداخت'), ('g', 'هدیه')], default='p', max_length=1, verbose_name='نوع'),
        ),
    ]