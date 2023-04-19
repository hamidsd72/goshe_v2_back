from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User 

UserAdmin.fieldsets += (
    ("فیلدها", {'fields': ('is_author','special_user','amount','link','avatar','timer','code','codeMelly','province','city','address')}),
)
 
admin.site.register(User, UserAdmin)
