from django.contrib import admin

from members.models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "status", "rank")
    list_filter = ("status", "rank")
    search_fields = ("name", "email")
