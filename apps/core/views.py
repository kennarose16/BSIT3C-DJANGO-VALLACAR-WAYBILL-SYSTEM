from calendar import monthrange
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.buses.models import Bus, BusRoute
from apps.drivers.models import Driver

User = get_user_model()

MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION = timedelta(minutes=1)
INVALID_LOGIN_MESSAGE = 'Invalid username or password.'
LOCKED_MESSAGE = 'Too many failed attempts. Locked for 1 minute.'


def _reset_lock_state(request):
    request.session['failed_attempts'] = 0
    request.session['lock_time'] = None


def _get_lock_state(request):
    failed_attempts = request.session.get('failed_attempts', 0)
    lock_time = request.session.get('lock_time')

    if not lock_time:
        return failed_attempts, None

    try:
        unlock_time = timezone.datetime.fromisoformat(lock_time)
    except (TypeError, ValueError):
        _reset_lock_state(request)
        return 0, None

    if timezone.now() < unlock_time:
        remaining = int((unlock_time - timezone.now()).total_seconds())
        return failed_attempts, remaining

    _reset_lock_state(request)
    return 0, None


def _set_lock_state(request):
    lock_until = timezone.now() + LOCK_DURATION
    request.session['failed_attempts'] = MAX_FAILED_ATTEMPTS
    request.session['lock_time'] = lock_until.isoformat()
    return int(LOCK_DURATION.total_seconds())


def _validate_registration_data(data):
    errors = {}

    username = data.get('username', '').strip()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not username:
        errors['username'] = 'Username is required.'
    elif User.objects.filter(username=username).exists():
        errors['username'] = 'Username already taken.'

    if not first_name:
        errors['first_name'] = 'First name is required.'

    if not last_name:
        errors['last_name'] = 'Last name is required.'

    if not email:
        errors['email'] = 'Email is required.'
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = 'Enter a valid email address.'
        else:
            if User.objects.filter(email=email).exists():
                errors['email'] = 'Email already registered.'

    if not password:
        errors['password'] = 'Password is required.'
    elif len(password) < 8:
        errors['password'] = 'Password must be at least 8 characters.'
    else:
        try:
            validate_password(password)
        except ValidationError as exc:
            errors['password'] = ' '.join(exc.messages)

    if password != confirm_password:
        errors['confirm_password'] = 'Passwords do not match.'

    return errors


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    failed_attempts, remaining = _get_lock_state(request)
    if remaining is not None:
        messages.error(request, f'Too many failed attempts. Try again in {remaining} seconds.')
        return render(request, 'auth/login.html', {'locked': True, 'remaining': remaining})

    if request.method == 'GET':
        return render(request, 'auth/login.html')

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    user = authenticate(request, username=username, password=password)

    if user is not None:
        _reset_lock_state(request)
        login(request, user)
        return redirect('dashboard')

    failed_attempts += 1
    request.session['failed_attempts'] = failed_attempts
    if failed_attempts >= MAX_FAILED_ATTEMPTS:
        remaining = _set_lock_state(request)
        messages.error(request, LOCKED_MESSAGE)
        return render(request, 'auth/login.html', {'locked': True, 'remaining': remaining})

    remaining_attempts = MAX_FAILED_ATTEMPTS - failed_attempts
    messages.error(request, f'{INVALID_LOGIN_MESSAGE} {remaining_attempts} attempts remaining.')
    return render(request, 'auth/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def _build_availability_calendar(year, month, active_bus_count, active_driver_count):
    first_day = date(year, month, 1)
    days_in_month = monthrange(year, month)[1]
    offset = first_day.weekday()
    cells = []

    for _ in range(offset):
        cells.append({'day': '', 'is_blank': True, 'available_buses': 0, 'available_drivers': 0})

    for day in range(1, days_in_month + 1):
        day_date = date(year, month, day)
        is_today = day_date == timezone.now().date()
        cells.append({
            'day': day,
            'is_blank': False,
            'is_today': is_today,
            'available_buses': active_bus_count,
            'available_drivers': active_driver_count,
        })

    while len(cells) % 7 != 0:
        cells.append({'day': '', 'is_blank': True, 'available_buses': 0, 'available_drivers': 0})

    return cells


@login_required(login_url='login')
def home(request):
    bus_count = Bus.objects.count()
    driver_count = Driver.objects.count()
    active_bus_count = Bus.objects.filter(status='active').count()
    active_driver_count = Driver.objects.filter(is_active=True).count()
    maintenance_bus_count = Bus.objects.filter(status='maintenance').count()

    operational_bus_percentage = round((active_bus_count / bus_count) * 100) if bus_count else 0
    driver_percentage = round((active_driver_count / driver_count) * 100) if driver_count else 0

    buses = Bus.objects.select_related('driver').prefetch_related('routes')[:6]
    recent_routes = BusRoute.objects.select_related('bus').filter(is_active=True)[:5]
    active_drivers = Driver.objects.filter(is_active=True)[:5]

    today = timezone.now().date()
    calendar_cells = _build_availability_calendar(today.year, today.month, active_bus_count, active_driver_count)

    technicians = [
        {'name': 'Maya Chen', 'role': 'Lead Electrician', 'status': 'Available', 'shift': '07:00 - 15:00', 'tone': 'success'},
        {'name': 'Jon Alvarez', 'role': 'Brake Specialist', 'status': 'On Call', 'shift': '09:00 - 17:00', 'tone': 'warning'},
        {'name': 'Trisha Cole', 'role': 'Diagnostics', 'status': 'Busy', 'shift': '08:00 - 16:00', 'tone': 'danger'},
        {'name': 'Omar Yusuf', 'role': 'Inspection', 'status': 'Available', 'shift': '12:00 - 20:00', 'tone': 'success'},
    ]

    alerts = [
        {'title': 'Bus 204 inspection overdue', 'detail': 'Brake check due 2 days ago', 'severity': 'critical'},
        {'title': 'Route 15 fuel anomaly', 'detail': 'Consumption 14% above baseline', 'severity': 'warning'},
        {'title': 'Driver 11 cert renewal', 'detail': 'License renewal pending this week', 'severity': 'info'},
    ]

    return render(request, 'home.html', {
        'driver_count': driver_count,
        'active_driver_count': active_driver_count,
        'bus_count': bus_count,
        'active_bus_count': active_bus_count,
        'route_count': BusRoute.objects.count(),
        'maintenance_bus_count': maintenance_bus_count,
        'operational_bus_percentage': operational_bus_percentage,
        'driver_percentage': driver_percentage,
        'buses': buses,
        'recent_routes': recent_routes,
        'active_drivers': active_drivers,
        'technicians': technicians,
        'alerts': alerts,
        'calendar_cells': calendar_cells,
        'calendar_month': today.strftime('%B %Y'),
        'today_date': today,
    })


@require_http_methods(['GET', 'POST'])
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'GET':
        return render(request, 'auth/register.html')

    form_data = {
        'username': request.POST.get('username', ''),
        'first_name': request.POST.get('first_name', ''),
        'last_name': request.POST.get('last_name', ''),
        'email': request.POST.get('email', ''),
        'password': request.POST.get('password', ''),
        'confirm_password': request.POST.get('confirm_password', ''),
    }

    errors = _validate_registration_data(form_data)
    if errors:
        return render(request, 'auth/register.html', {'errors': errors, 'form_data': form_data})

    user = User.objects.create_user(
        username=form_data['username'].strip(),
        first_name=form_data['first_name'].strip(),
        last_name=form_data['last_name'].strip(),
        email=form_data['email'].strip(),
        password=form_data['password'],
    )
    login(request, user)
    return redirect('dashboard')
