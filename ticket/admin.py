from django.contrib import admin
from .models import Ticket

class TicketAdmin(admin.ModelAdmin):
    list_display        = ('userId' ,"sendTo" ,'subject' ,'content' ,'baner' ,'created_at' ,'updated_at' )
    list_filter         = (['userId'])
    search_fields       = ('userId','sendTo')
    # prepopulated_fields = {'type': ('userId',)}
    ordering            = ['-id'] 

admin.site.register(Ticket, TicketAdmin)
