from django.contrib import admin
from .models import UserProfile, Internship, Application

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'skills')

@admin.register(Internship)
class InternshipAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'location', 'interest_area', 'created_at')
    search_fields = ('company_name', 'location', 'skills_required')

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'internship', 'applied_at', 'status')
    list_filter = ('status',)
