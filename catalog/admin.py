from django.contrib import admin

from catalog.models import Copy, Title


class CopyInline(admin.TabularInline):
    model = Copy
    extra = 1


@admin.register(Title)
class TitleAdmin(admin.ModelAdmin):
    list_display = ("name", "author", "isbn")
    search_fields = ("name", "author", "isbn")
    inlines = [CopyInline]


@admin.register(Copy)
class CopyAdmin(admin.ModelAdmin):
    list_display = ("title", "copy_number", "status")
    list_filter = ("status",)
    search_fields = ("title__name",)
