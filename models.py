"""
Database models for the Travel Booking Application
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.urls import reverse
import uuid


class TravelOption(models.Model):
    """Model representing a travel option (flight, train, or bus)"""
    
    TRAVEL_TYPES = (
        ('FLIGHT', 'Flight'),
        ('TRAIN', 'Train'),
        ('BUS', 'Bus'),
    )
    
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('CANCELLED', 'Cancelled'),
        ('FULL', 'Fully Booked'),
    )
    
    travel_id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    travel_code = models.CharField(
        max_length=20, 
        unique=True,
        help_text="e.g., FL123, TR456, BS789"
    )
    type = models.CharField(
        max_length=10, 
        choices=TRAVEL_TYPES
    )
    company_name = models.CharField(
        max_length=100,
        help_text="Name of the airline/railway/bus company"
    )
    source = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    total_seats = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(500)]
    )
    available_seats = models.IntegerField(
        validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='ACTIVE'
    )
    amenities = models.TextField(
        blank=True,
        help_text="Comma-separated list of amenities"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['departure_time']
        indexes = [
            models.Index(fields=['source', 'destination']),
            models.Index(fields=['departure_time']),
            models.Index(fields=['type']),
        ]
    
    def __str__(self):
        return f"{self.travel_code} - {self.source} to {self.destination}"
    
    def get_absolute_url(self):
        return reverse('travel_detail', kwargs={'pk': self.travel_id})
    
    def duration(self):
        """Calculate journey duration"""
        delta = self.arrival_time - self.departure_time
        hours = delta.total_seconds() // 3600
        minutes = (delta.total_seconds() % 3600) // 60
        return f"{int(hours)}h {int(minutes)}m"
    
    def is_available(self):
        """Check if seats are available"""
        return self.available_seats > 0 and self.status == 'ACTIVE'
    
    def update_availability(self, seats_booked):
        """Update available seats after booking"""
        self.available_seats -= seats_booked
        if self.available_seats == 0:
            self.status = 'FULL'
        self.save()
    
    def cancel_seats(self, seats_cancelled):
        """Restore seats after cancellation"""
        self.available_seats += seats_cancelled
        if self.status == 'FULL' and self.available_seats > 0:
            self.status = 'ACTIVE'
        self.save()
    
    @property
    def occupancy_rate(self):
        """Calculate occupancy percentage"""
        if self.total_seats == 0:
            return 0
        booked = self.total_seats - self.available_seats
        return round((booked / self.total_seats) * 100, 2)


class Booking(models.Model):
    """Model representing a booking made by a user"""
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    )
    
    booking_id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    booking_reference = models.CharField(
        max_length=20, 
        unique=True,
        editable=False
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    travel_option = models.ForeignKey(
        TravelOption, 
        on_delete=models.PROTECT,
        related_name='bookings'
    )
    number_of_seats = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    total_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2
    )
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='PENDING'
    )
    passenger_details = models.JSONField(
        default=list,
        help_text="List of passenger information"
    )
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=15)
    special_requirements = models.TextField(blank=True)
    payment_id = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Payment gateway transaction ID"
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-booking_date']
        indexes = [
            models.Index(fields=['user', '-booking_date']),
            models.Index(fields=['status']),
            models.Index(fields=['booking_reference']),
        ]
    
    def __str__(self):
        return f"{self.booking_reference} - {self.user.username}"
    
    def get_absolute_url(self):
        return reverse('booking_detail', kwargs={'pk': self.booking_id})
    
    def save(self, *args, **kwargs):
        if not self.booking_reference:
            # Generate unique booking reference
            prefix = self.travel_option.type[:2].upper()
            timestamp = timezone.now().strftime('%Y%m%d%H%M')
            random_suffix = str(uuid.uuid4())[:4].upper()
            self.booking_reference = f"{prefix}{timestamp}{random_suffix}"
        
        if not self.pk:
            # Calculate total price for new bookings
            self.total_price = self.travel_option.price * self.number_of_seats
        
        super().save(*args, **kwargs)
    
    def cancel(self, reason=''):
        """Cancel the booking"""
        if self.status == 'CONFIRMED':
            self.status = 'CANCELLED'
            self.cancelled_at = timezone.now()
            self.cancellation_reason = reason
            self.travel_option.cancel_seats(self.number_of_seats)
            self.save()
            return True
        return False
    
    def confirm(self):
        """Confirm the booking"""
        if self.status == 'PENDING':
            self.status = 'CONFIRMED'
            self.save()
            return True
        return False
    
    def is_cancellable(self):
        """Check if booking can be cancelled"""
        if self.status != 'CONFIRMED':
            return False
        # Can cancel up to 2 hours before departure
        time_until_departure = self.travel_option.departure_time - timezone.now()
        return time_until_departure.total_seconds() > 7200  # 2 hours
    
    def get_refund_amount(self):
        """Calculate refund amount based on cancellation policy"""
        if not self.is_cancellable():
            return 0
        
        time_until_departure = self.travel_option.departure_time - timezone.now()
        hours_until = time_until_departure.total_seconds() / 3600
        
        if hours_until > 24:
            return float(self.total_price) * 0.9  # 90% refund
        elif hours_until > 6:
            return float(self.total_price) * 0.5  # 50% refund
        else:
            return float(self.total_price) * 0.25  # 25% refund


class UserProfile(models.Model):
    """Extended user profile model"""
    
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='profile'
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True
    )
    date_of_birth = models.DateField(
        null=True, 
        blank=True
    )
    gender = models.CharField(
        max_length=1, 
        choices=GENDER_CHOICES,
        blank=True
    )
    address = models.TextField(blank=True)
    city = models.CharField(max_length=50, blank=True)
    state = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, default='India')
    pincode = models.CharField(max_length=10, blank=True)
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        blank=True,
        null=True
    )
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def get_full_address(self):
        """Get complete address"""
        parts = [self.address, self.city, self.state, self.country, self.pincode]
        return ', '.join(filter(None, parts))
    
    @property
    def total_bookings(self):
        """Get total number of bookings"""
        return self.user.bookings.count()
    
    @property
    def active_bookings(self):
        """Get number of active bookings"""
        return self.user.bookings.filter(status='CONFIRMED').count()


# Signal to create user profile automatically
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()