from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.db.models import Q
from .models import Schedule, Appointment
from .forms import RegistrationForm, LoginForm

def register_view(request):
    if request.user.is_authenticated: return redirect('schedule')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Добро пожаловать, {user.username}!")
            return redirect('schedule')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated: return redirect('schedule')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('schedule')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('schedule')

def schedule_view(request):
    schedules = Schedule.objects.filter(is_available=True).select_related('doctor')
    query = request.GET.get('q', '').strip()
    if query:
        schedules = schedules.filter(
            Q(doctor__name__icontains=query) |
            Q(doctor__specialization__icontains=query)
        )
    return render(request, 'schedule.html', {'schedules': schedules, 'search_query': query})

@login_required
def make_appointment(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id, is_available=True)
    if Appointment.objects.filter(patient=request.user, schedule=schedule, status__in=['pending', 'confirmed']).exists():
        messages.warning(request, "Вы уже записаны на это время.")
        return redirect('schedule')
    
    Appointment.objects.create(patient=request.user, schedule=schedule, status='pending')
    schedule.is_available = False
    schedule.save()
    messages.success(request, f"Вы записаны к {schedule.doctor} на {schedule.date} в {schedule.time}")
    return redirect('my_appointments')

@login_required
def my_appointments(request):
    appointments = Appointment.objects.filter(patient=request.user).select_related('schedule__doctor').order_by('-created_at')
    return render(request, 'my_appointments.html', {'appointments': appointments})

@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    appointment.status = 'cancelled'
    appointment.save()
    appointment.schedule.is_available = True
    appointment.schedule.save()
    messages.info(request, "Запись отменена.")
    return redirect('my_appointments')