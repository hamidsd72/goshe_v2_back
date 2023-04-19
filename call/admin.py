from django.contrib import admin
from .models import CallLog, Number

class CallLogAdmin(admin.ModelAdmin):
    list_display = ('id','Sitak_id','userId','authorId','type','FirstCredit','call_amount','AmountPerMin','created_at','updated_at','jpublish')
    list_filter  = (['type'])
    # search_fields       = ('title','slug')
    # prepopulated_fields = {'slug': ('title',)}
    # ordering            = ['slug']

admin.site.register(CallLog, CallLogAdmin)
# ====================================================================================
class NumbersLogAdmin(admin.ModelAdmin):
    list_display = ('id','userId','number','subject','created_at','updated_at','jpublish')
    list_filter  = (['userId','number'])
    # search_fields       = ('title','slug')
    # prepopulated_fields = {'slug': ('title',)}
    # ordering            = ['slug']

admin.site.register(Number, NumbersLogAdmin)
# ====================================================================================

