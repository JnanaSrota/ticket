"""
URL Configuration for the Booking App
"""

from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [    
    # Authentication URLs
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Basic pages
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    
    # Travel listings
    path('travels/', views.travel_list_view, name='travel_list'),
    path('travels/<uuid:pk>/', views.travel_detail_view, name='travel_detail'),
    path('search/suggestions/', views.search_suggestions_view, name='search_suggestions'),
    
    # Booking management
    path('travels/<uuid:pk>/book/', views.book_travel_view, name='book_travel'),
    path('bookings/', views.my_bookings_view, name='my_bookings'),
    path('bookings/<uuid:pk>/', views.booking_detail_view, name='booking_detail'),
    path('bookings/<uuid:pk>/cancel/', views.cancel_booking_view, name='cancel_booking'),
    path('bookings/<uuid:pk>/confirmation/', views.booking_confirmation_view, name='booking_confirmation'),
    path('bookings/<uuid:pk>/ticket/', views.download_ticket_view, name='download_ticket'),
    
    # User profile
    path('profile/', views.profile_view, name='profile'),
]