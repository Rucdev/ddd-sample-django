from django.contrib import admin

from customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "status", "rank", "points")
    list_filter = ("status", "rank")
    search_fields = ("name", "email")
