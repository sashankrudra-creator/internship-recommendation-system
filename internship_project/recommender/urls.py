from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('recommendations/', views.recommendations, name='recommendations'),
    path('all-internships/', views.all_internships, name='all_internships'),
    path('apply/<int:pk>/', views.apply_internship, name='apply_internship'),
    path('history/', views.application_history, name='application_history'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('sync-csv/', views.sync_from_csv, name='sync_from_csv'),
    path('external-apply-dummy/', views.external_apply_dummy, name='external_apply_dummy'),
    path('saved/', views.saved_internships, name='saved_internships'),
    path('save/<int:pk>/', views.toggle_save_internship, name='toggle_save_internship'),
    path('trends/', views.trends, name='trends'),
]