from django.contrib import admin

from members.models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "status")
    list_filter = ("status",)
    search_fields = ("name", "email")
