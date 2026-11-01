from django.contrib import admin

from menu.models import Category, MenuItem


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order")
    inlines = [MenuItemInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "status", "has_image")
    list_filter = ("category", "status")
    list_editable = ("status",)
    search_fields = ("name",)

    @admin.display(boolean=True, description="画像")
    def has_image(self, obj: MenuItem) -> bool:
        return bool(obj.image)
