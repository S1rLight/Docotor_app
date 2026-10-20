from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.db.models import Q
from .models import Schedule, Appointment
from .forms import RegistrationForm, LoginForm
from django.utils import timezone

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
    today = timezone.now().date()
    schedules = Schedule.objects.filter(is_available=True, date__gte=today).select_related('doctor')
    
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
    
    if schedule.date < timezone.now().date():
        messages.error(request, "Нельзя записаться на прошедшую дату.")
        return redirect('schedule')

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
    
    now = timezone.now()  
    
    for appt in appointments:
        if appt.schedule.date < now.date():
            if appt.status in ['pending', 'confirmed']:
                appt.status = 'completed'
                appt.save()
        elif appt.schedule.date == now.date() and appt.schedule.time < now.time():
            if appt.status in ['pending', 'confirmed']:
                appt.status = 'completed'
                appt.save()
    
    return render(request, 'my_appointments.html', {'appointments': appointments})

@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user)
    
    if appointment.status in ['cancelled', 'completed']:
        messages.warning(request, "Эту запись нельзя отменить.")
        return redirect('my_appointments')
    
    now = timezone.now()
    today = now.date()
    current_time = now.time()
    
    is_past = appointment.schedule.date < today or (appointment.schedule.date == today and appointment.schedule.time < current_time)
    
    if is_past:
        messages.error(request, "Нельзя отменить запись, время приёма уже прошло.")
        return redirect('my_appointments')

    appointment.status = 'cancelled'
    appointment.save()
    appointment.schedule.is_available = True
    appointment.schedule.save()
    messages.info(request, "Запись отменена.")
    return redirect('my_appointments')