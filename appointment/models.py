from django.db import models
from django.contrib.auth.models import User

class Doctor(models.Model):
    name = models.CharField(max_length=200, verbose_name="ФИО доктора")
    specialization = models.CharField(max_length=100, verbose_name="Специализация")
    experience = models.IntegerField(verbose_name="Стаж (лет)", default=0)

    class Meta:
        verbose_name = "Доктор"
        verbose_name_plural = "Доктора"

    def __str__(self):
        return f"{self.name} — {self.specialization}"

class Schedule(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="schedules")
    date = models.DateField(verbose_name="Дата приёма")
    time = models.TimeField(verbose_name="Время приёма")
    is_available = models.BooleanField(default=True, verbose_name="Свободно")

    class Meta:
        verbose_name = "Расписание"
        verbose_name_plural = "Расписание"
        ordering = ['date', 'time']

    def __str__(self):
        return f"{self.doctor} — {self.date} {self.time}"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('confirmed', 'Подтверждена'),
        ('cancelled', 'Отменена'),
    ]
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="appointments")
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Запись"
        verbose_name_plural = "Записи"

    def __str__(self):
        return f"{self.patient.username} -> {self.schedule.doctor} ({self.schedule.date})"