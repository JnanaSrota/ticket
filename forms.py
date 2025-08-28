"""
Forms for the Travel Booking Application
"""

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Booking, UserProfile, TravelOption
import re


class UserRegistrationForm(forms.ModelForm):
    """User registration form"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        }),
        min_length=8,
        help_text='Password must be at least 8 characters long'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        }),
        label='Confirm Password'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email'
        }),
        required=True
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
        }
    
    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise ValidationError('Passwords do not match')
        
        return password_confirm
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Email already registered')
        return email
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        
        # Password strength validation
        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', password):
            raise ValidationError('Password must contain at least one digit')
        
        return password


class LoginForm(forms.Form):
    """User login form"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class UserProfileForm(forms.ModelForm):
    """User profile edit form"""
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'phone_number', 'date_of_birth', 'gender',
            'address', 'city', 'state', 'country', 'pincode',
            'profile_picture', 'email_notifications', 'sms_notifications'
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91 9876543210'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            # Remove spaces and hyphens
            phone_number = phone_number.replace(' ', '').replace('-', '')
            # Validate phone number format
            if not re.match(r'^[+]?[0-9]{10,15}$', phone_number):
                raise ValidationError('Enter a valid phone number')
        return phone_number
    
    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode')
        if pincode and not re.match(r'^[0-9]{6}$', pincode):
            raise ValidationError('Enter a valid 6-digit pincode')
        return pincode


class BookingForm(forms.ModelForm):
    """Booking form for travel options"""
    
    passenger_names = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter passenger names (one per line)'
        }),
        help_text='Enter one passenger name per line',
        required=True
    )
    
    agree_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='I agree to the terms and conditions'
    )
    
    class Meta:
        model = Booking
        fields = [
            'number_of_seats', 'contact_email', 'contact_phone',
            'special_requirements'
        ]
        widgets = {
            'number_of_seats': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '10'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91 9876543210'
            }),
            'special_requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any special requirements? (Optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        max_seats = kwargs.pop('max_seats', 10)
        super().__init__(*args, **kwargs)
        self.fields['number_of_seats'].widget.attrs['max'] = str(max_seats)
        self.fields['number_of_seats'].help_text = f'Maximum {max_seats} seats available'
    
    def clean_passenger_names(self):
        passenger_names = self.cleaned_data.get('passenger_names', '')
        names = [name.strip() for name in passenger_names.split('\n') if name.strip()]
        
        number_of_seats = self.cleaned_data.get('number_of_seats', 0)
        if len(names) != number_of_seats:
            raise ValidationError(
                f'Please enter exactly {number_of_seats} passenger name(s)'
            )
        
        return names
    
    def clean_contact_phone(self):
        phone = self.cleaned_data.get('contact_phone')
        if phone:
            phone = phone.replace(' ', '').replace('-', '')
            if not re.match(r'^[+]?[0-9]{10,15}$', phone):
                raise ValidationError('Enter a valid phone number')
        return phone
    
    def save(self, commit=True):
        booking = super().save(commit=False)
        
        # Convert passenger names to JSON format
        passenger_names = self.cleaned_data.get('passenger_names', [])
        booking.passenger_details = [
            {'name': name, 'seat_number': i+1} 
            for i, name in enumerate(passenger_names)
        ]
        
        if commit:
            booking.save()
        return booking


class TravelSearchForm(forms.Form):
    """Search form for travel options"""
    
    TRAVEL_TYPE_CHOICES = [('', 'All Types')] + list(TravelOption.TRAVEL_TYPES)
    
    travel_type = forms.ChoiceField(
        choices=TRAVEL_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    source = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'From city...'
        })
    )
    destination = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'To city...'
        })
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='From Date'
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='To Date'
    )
    min_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min price',
            'min': '0'
        })
    )
    max_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max price',
            'min': '0'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        
        # Validate date range
        if date_from and date_to and date_from > date_to:
            raise ValidationError('From date cannot be after To date')
        
        # Validate price range
        if min_price and max_price and min_price > max_price:
            raise ValidationError('Minimum price cannot be greater than maximum price')
        
        return cleaned_data


class ContactForm(forms.Form):
    """Contact form for inquiries"""
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Email'
        })
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Your Message'
        })
    )


class PasswordChangeForm(forms.Form):
    """Custom password change form"""
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current Password'
        })
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New Password'
        }),
        min_length=8
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm New Password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise ValidationError('New passwords do not match')
            
            # Password strength validation
            if not re.search(r'[A-Z]', new_password):
                raise ValidationError('Password must contain at least one uppercase letter')
            if not re.search(r'[a-z]', new_password):
                raise ValidationError('Password must contain at least one lowercase letter')
            if not re.search(r'[0-9]', new_password):
                raise ValidationError('Password must contain at least one digit')
        
        return cleaned_data