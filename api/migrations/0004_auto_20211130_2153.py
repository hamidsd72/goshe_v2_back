# Generated by Django 3.2.7 on 2021-11-30 21:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_document_userid'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='card_no',
            field=models.CharField(max_length=250, null=True, verbose_name='شماره کارت پرداخت'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='idPay_id',
            field=models.CharField(max_length=250, null=True, verbose_name='شماره آیدی پی'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='link',
            field=models.CharField(max_length=250, null=True, verbose_name='لینک آیدی پی'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='payment',
            field=models.CharField(max_length=250, null=True, verbose_name='اطلاعات پرداخت تراکنش آیدی پی'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='status',
            field=models.IntegerField(null=True, verbose_name='وضعیت آیدی پی'),
        ),
        migrations.AddField(
            model_name='transaction',
            name='track_id',
            field=models.IntegerField(null=True, verbose_name='کد رهگیری آیدی پی'),
        ),
    ]
