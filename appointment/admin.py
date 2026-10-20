from django.contrib import admin
from .models import Doctor, Schedule, Appointment


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['name', 'specialization', 'experience']


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
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