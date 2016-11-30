from django.contrib import admin
from .models import *


admin.site.register(Article)
admin.site.register(Blog)
admin.site.register(MailTemplate)
admin.site.register(CustomUser)
admin.site.register(CustomImage)
admin.site.register(Category)
# admin.site.register(Mail)