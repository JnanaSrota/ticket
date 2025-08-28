"""
Views for the Travel Booking Application
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, DetailView
from django.db import transaction
from django.contrib.auth.models import User
from prompt_toolkit import HTML

from .models import TravelOption, Booking, UserProfile
from .forms import (
    UserRegistrationForm, UserProfileForm, 
    BookingForm, TravelSearchForm, LoginForm
)

import json
from datetime import datetime, timedelta
from django.template.loader import render_to_string
from weasyprint import HTML


def home_view(request):
    """Home page with featured travel options"""
    featured_travels = TravelOption.objects.filter(
        status='ACTIVE',
        departure_time__gte=timezone.now()
    ).order_by('departure_time')[:6]
    
    # Get statistics
    stats = {
        'total_destinations': TravelOption.objects.values('destination').distinct().count(),
        'active_routes': TravelOption.objects.filter(status='ACTIVE').count(),
        'happy_customers': Booking.objects.filter(status='CONFIRMED').values('user').distinct().count(),
        'available_today': TravelOption.objects.filter(
            status='ACTIVE',
            departure_time__date=timezone.now().date()
        ).count()
    }
    
    context = {
        'featured_travels': featured_travels,
        'stats': stats,
    }
    return render(request, 'booking/home.html', context)


def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Create user profile
            UserProfile.objects.get_or_create(user=user)
            
            # Auto-login after registration
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to Travel Booking.')
            return redirect('profile')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'booking/register.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    
    return render(request, 'booking/login.html', {'form': form})


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def profile_view(request):
    """User profile view and edit"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            
            # Update User model fields
            request.user.first_name = form.cleaned_data.get('first_name', '')
            request.user.last_name = form.cleaned_data.get('last_name', '')
            request.user.email = form.cleaned_data.get('email', '')
            request.user.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        }
        form = UserProfileForm(instance=profile, initial=initial_data)
    
    # Get user's recent bookings
    recent_bookings = Booking.objects.filter(
        user=request.user
    ).order_by('-booking_date')[:5]
    
    context = {
        'form': form,
        'profile': profile,
        'recent_bookings': recent_bookings,
    }
    return render(request, 'booking/profile.html', context)


def travel_list_view(request):
    """List all available travel options with search and filter"""
    travels = TravelOption.objects.filter(
        departure_time__gte=timezone.now()
    ).order_by('departure_time')
    
    # Search and filter
    search_form = TravelSearchForm(request.GET)
    
    if search_form.is_valid():
        travel_type = search_form.cleaned_data.get('travel_type')
        source = search_form.cleaned_data.get('source')
        destination = search_form.cleaned_data.get('destination')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        min_price = search_form.cleaned_data.get('min_price')
        max_price = search_form.cleaned_data.get('max_price')
        
        if travel_type:
            travels = travels.filter(type=travel_type)
        if source:
            travels = travels.filter(source__icontains=source)
        if destination:
            travels = travels.filter(destination__icontains=destination)
        if date_from:
            travels = travels.filter(departure_time__date__gte=date_from)
        if date_to:
            travels = travels.filter(departure_time__date__lte=date_to)
        if min_price:
            travels = travels.filter(price__gte=min_price)
        if max_price:
            travels = travels.filter(price__lte=max_price)
    
    # Only show active travels
    travels = travels.filter(status='ACTIVE')
    
    # Pagination
    paginator = Paginator(travels, 9)  # Show 9 travels per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_results': travels.count(),
    }
    return render(request, 'booking/travel_list.html', context)


def travel_detail_view(request, pk):
    """Detailed view of a single travel option"""
    travel = get_object_or_404(TravelOption, pk=pk)
    
    # Check if user has already booked this travel
    user_has_booking = False
    if request.user.is_authenticated:
        user_has_booking = Booking.objects.filter(
            user=request.user,
            travel_option=travel,
            status='CONFIRMED'
        ).exists()
    
    # Get similar travel options
    similar_travels = TravelOption.objects.filter(
        Q(source=travel.source) | Q(destination=travel.destination),
        status='ACTIVE',
        departure_time__gte=timezone.now()
    ).exclude(pk=pk)[:4]
    
    context = {
        'travel': travel,
        'user_has_booking': user_has_booking,
        'similar_travels': similar_travels,
        'can_book': travel.is_available() and not user_has_booking,
    }
    return render(request, 'booking/travel_detail.html', context)


@login_required
@transaction.atomic
def book_travel_view(request, pk):
    """Book a travel option"""
    travel = get_object_or_404(TravelOption, pk=pk)
    
    if not travel.is_available():
        messages.error(request, 'This travel option is no longer available.')
        return redirect('travel_detail', pk=pk)
    
    if request.method == 'POST':
        form = BookingForm(request.POST, max_seats=travel.available_seats)
        if form.is_valid():
            # Check availability again (race condition prevention)
            if travel.available_seats < form.cleaned_data['number_of_seats']:
                messages.error(request, f'Only {travel.available_seats} seats available.')
                return redirect('travel_detail', pk=pk)
            
            # Create booking
            booking = form.save(commit=False)
            booking.user = request.user
            booking.travel_option = travel
            booking.total_price = travel.price * booking.number_of_seats
            booking.save()
            
            # Update travel availability
            travel.update_availability(booking.number_of_seats)
            
            messages.success(request, f'Booking confirmed! Reference: {booking.booking_reference}')
            return redirect('booking_detail', pk=booking.pk)
    else:
        initial_data = {
            'contact_email': request.user.email,
            'contact_phone': request.user.profile.phone_number if hasattr(request.user, 'profile') else '',
        }
        form = BookingForm(initial=initial_data, max_seats=travel.available_seats)
    
    context = {
        'travel': travel,
        'form': form,
    }
    return render(request, 'booking/book_travel.html', context)


@login_required
def booking_detail_view(request, pk):
    """View booking details"""
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    
    context = {
        'booking': booking,
        'can_cancel': booking.is_cancellable(),
        'refund_amount': booking.get_refund_amount() if booking.is_cancellable() else 0,
    }
    return render(request, 'booking/booking_detail.html', context)


@login_required
def my_bookings_view(request):
    """View all user bookings"""
    bookings = Booking.objects.filter(user=request.user).order_by('-booking_date')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    # Separate upcoming and past bookings
    current_time = timezone.now()
    upcoming_bookings = []
    past_bookings = []
    
    for booking in bookings:
        if booking.travel_option.departure_time >= current_time:
            upcoming_bookings.append(booking)
        else:
            past_bookings.append(booking)
    
    # Pagination
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'upcoming_bookings': upcoming_bookings[:5],
        'past_bookings': past_bookings[:5],
        'status_filter': status_filter,
    }
    return render(request, 'booking/my_bookings.html', context)


@login_required
@require_http_methods(["POST"])
def cancel_booking_view(request, pk):
    """Cancel a booking"""
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    
    if not booking.is_cancellable():
        messages.error(request, 'This booking cannot be cancelled.')
        return redirect('booking_detail', pk=pk)
    
    # Process cancellation
    reason = request.POST.get('cancellation_reason', '')
    if booking.cancel(reason):
        refund_amount = booking.get_refund_amount()
        messages.success(
            request, 
            f'Booking cancelled successfully. Refund amount: ₹{refund_amount:.2f}'
        )
    else:
        messages.error(request, 'Failed to cancel booking.')
    
    return redirect('my_bookings')


@login_required
def booking_confirmation_view(request, pk):
    """Show booking confirmation page"""
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    
    # Only show confirmation for recently confirmed bookings
    time_since_booking = timezone.now() - booking.booking_date
    if time_since_booking.total_seconds() > 3600:  # 1 hour
        return redirect('booking_detail', pk=pk)
    
    context = {
        'booking': booking,
    }
    return render(request, 'booking/booking_confirmation.html', context)


def search_suggestions_view(request):
    """AJAX view for search suggestions"""
    query = request.GET.get('q', '')
    field = request.GET.get('field', 'destination')
    
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    if field == 'source':
        suggestions = TravelOption.objects.filter(
            source__icontains=query
        ).values_list('source', flat=True).distinct()[:10]
    else:
        suggestions = TravelOption.objects.filter(
            destination__icontains=query
        ).values_list('destination', flat=True).distinct()[:10]
    
    return JsonResponse({'suggestions': list(suggestions)})


@login_required
def download_ticket_view(request, pk):
    """Generate and download ticket PDF"""
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    
    if booking.status != 'CONFIRMED':
        messages.error(request, 'Only confirmed bookings can be downloaded.')
        return redirect('booking_detail', pk=pk)
    
    html_string = render_to_string('booking/ticket_pdf.html', {'booking': booking})
    
    # Generate PDF
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    result = html.write_pdf()

    # Return response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{booking.booking_reference}.pdf"'
    response.write(result)
    return response
    context = {
        'booking': booking,
    }
    return render(request, 'booking/ticket_print.html', context)


def about_view(request):
    """About page"""
    return render(request, 'booking/about.html')


def contact_view(request):
    """Contact page"""
    if request.method == 'POST':
        # Handle contact form submission
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        # In production, you would send an email or save to database
        messages.success(request, 'Thank you for contacting us! We will get back to you soon.')
        return redirect('contact')
    
    return render(request, 'booking/contact.html')