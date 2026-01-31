from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Address

class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = UserAdmin.fieldsets + (
        ('Nexus Profile', {'fields': ('role', 'profile_picture', 'bio', 'is_verified')}),
    )
    list_display = ['username', 'email', 'role', 'is_verified', 'is_staff']
    list_filter = ['role', 'is_verified', 'is_staff']

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'city', 'country', 'is_default']
    search_fields = ['user__username', 'street', 'city']

admin.site.register(User, CustomUserAdmin)
