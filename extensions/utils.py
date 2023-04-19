from . import jalali
from django.utils import timezone

def jalali_converter(time):
    # jmonth = [ "farvardin" ,"ordibehesht" ,"khordad" ,"tir" ,"mordad" ,"shahrivar" ,"mehr" ,"aban" ,"azar" ,"dey" ,"bahman" ,"esfand" ]
    jmonth = [ "فروردین" ,"اردیبهشت" ,"خرداد" ,"تیر" ,"مرداد" ,"شهریور" ,"مهر" ,"آبان" ,"آذر" ,"دی" ,"بهمن" ,"اسفند" ]
    time = timezone.localtime(time)

    time_to_str = "{},{},{}".format(time.year, time.month, time.day)

    per_time = jalali.Gregorian(time_to_str).persian_tuple()

    per_time_to_list = list(per_time)
    for index, month in enumerate(jmonth):
        if per_time_to_list[1] == index + 1:
            per_time_to_list[1] = month
            break

    return "{} {} {}. ساعت {}:{} تاریخ".format(
        per_time_to_list[2], per_time_to_list[1], per_time_to_list[0],
        time.hour, time.minute
    )
