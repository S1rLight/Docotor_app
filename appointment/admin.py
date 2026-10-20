from django.contrib import admin
from .models import Doctor, Schedule, Appointment
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['name', 'specialization', 'experience']

class ScheduleAdminForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        if date and date < timezone.now().date():
            raise ValidationError("Нельзя создавать или редактировать расписание на прошедшие даты.")
        return cleaned_data


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    form = ScheduleAdminForm
    list_display = ['doctor', 'date', 'time', 'is_available']
    list_filter = ['doctor', 'date']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'schedule', 'status', 'created_at']
    list_filter = ['status']
    actions = ['confirm_appointments', 'cancel_appointments']

    @admin.action(description='Подтвердить выбранные записи')
    def confirm_appointments(self, request, queryset):
        queryset.update(status='confirmed')

    @admin.action(description='Отменить выбранные записи (освободить слоты)')
    def cancel_appointments(self, request, queryset):
        for appointment in queryset:
            appointment.status = 'cancelled'
            appointment.save()
            appointment.schedule.is_available = True
            appointment.schedule.save()