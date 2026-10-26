from django.contrib import admin

from menu.models import Category, MenuItem


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1
    readonly_fields = ("out_of_stock",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order")
    inlines = [MenuItemInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "status", "out_of_stock")
    list_filter = ("category", "status", "out_of_stock")
    list_editable = ("status",)
    search_fields = ("name",)
    # 在庫切れは inventory が在庫数に合わせて切り替えるので、admin からは触らせない。
    readonly_fields = ("out_of_stock",)
