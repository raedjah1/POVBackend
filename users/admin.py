from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import SignInCodeRequest, User, Interest, Spectator, Creator

admin.site.register(User, UserAdmin)
admin.site.register(Interest)
admin.site.register(Spectator)
admin.site.register(Creator)
admin.site.register(SignInCodeRequest)
