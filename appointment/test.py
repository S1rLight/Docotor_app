from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .forms import RegistrationForm
from .models import Appointment, Doctor, Schedule


# ---------------------------------------------------------------------------
# Фабричные методы (паттерн Object Mother из методички)
# ---------------------------------------------------------------------------
def create_doctor(name='Иванов Иван Иванович', specialization='Терапевт', experience=10):
    return Doctor.objects.create(name=name, specialization=specialization, experience=experience)


def create_schedule(doctor=None, days_offset=1, at=time(12, 0), available=True):
    doctor = doctor or create_doctor()
    return Schedule.objects.create(
        doctor=doctor,
        date=date.today() + timedelta(days=days_offset),
        time=at,
        is_available=available,
    )


def create_user(username='patient', password='TestPass123!', email='patient@mail.ru'):
    return User.objects.create_user(username=username, email=email, password=password)


# ---------------------------------------------------------------------------
# Unit-тесты моделей
# ---------------------------------------------------------------------------
class DoctorModelTest(TestCase):
    """Модульные тесты модели Doctor"""

    def setUp(self):
        self.doctor = create_doctor()  # Arrange

    def test_fields_saved_correctly(self):
        self.assertEqual(self.doctor.name, 'Иванов Иван Иванович')   # Assert
        self.assertEqual(self.doctor.specialization, 'Терапевт')
        self.assertEqual(self.doctor.experience, 10)

    def test_str_representation(self):
        self.assertEqual(str(self.doctor), 'Иванов Иван Иванович — Терапевт')

    def test_experience_default_value(self):
        doctor = Doctor.objects.create(name='Без Стажа', specialization='Хирург')
        self.assertEqual(doctor.experience, 0)


class ScheduleModelTest(TestCase):
    """Модульные тесты модели Schedule"""

    def setUp(self):
        self.doctor = create_doctor()

    def test_is_available_by_default(self):
        schedule = Schedule.objects.create(doctor=self.doctor, date=date.today(), time=time(9, 0))
        self.assertTrue(schedule.is_available)

    def test_str_representation(self):
        schedule = create_schedule(self.doctor)
        expected = f'{schedule.doctor} — {schedule.date} {schedule.time}'
        self.assertEqual(str(schedule), expected)

    def test_ordering_by_date_and_time(self):
        earlier = create_schedule(self.doctor, days_offset=0, at=time(8, 0))
        later = create_schedule(self.doctor, days_offset=2, at=time(18, 0))
        schedules = list(Schedule.objects.all())
        self.assertEqual(schedules[0], earlier)
        self.assertEqual(schedules[-1], later)


class AppointmentModelTest(TestCase):
    """Модульные тесты модели Appointment"""

    def setUp(self):
        self.user = create_user()
        self.schedule = create_schedule()

    def test_default_status_is_pending(self):
        appointment = Appointment.objects.create(patient=self.user, schedule=self.schedule)
        self.assertEqual(appointment.status, 'pending')

    def test_str_representation(self):
        appointment = Appointment.objects.create(patient=self.user, schedule=self.schedule)
        expected = f'{self.user.username} -> {self.schedule.doctor} ({self.schedule.date})'
        self.assertEqual(str(appointment), expected)

    def test_status_choices_contain_all_statuses(self):
        codes = [code for code, _ in Appointment.STATUS_CHOICES]
        for expected in ('pending', 'confirmed', 'cancelled', 'completed'):
            self.assertIn(expected, codes)


# ---------------------------------------------------------------------------
# Unit-тесты формы регистрации
# ---------------------------------------------------------------------------
class RegistrationFormTest(TestCase):
    """Модульные тесты валидации формы регистрации"""

    def _data(self, **overrides):
        data = {
            'username': 'newpatient',
            'first_name': 'Иван',
            'last_name': 'Петров',
            'email': 'new@mail.ru',
            'password1': 'Str0ngPass!23',
            'password2': 'Str0ngPass!23',
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = RegistrationForm(data=self._data())
        self.assertTrue(form.is_valid())

    def test_password_mismatch_rejected(self):
        form = RegistrationForm(data=self._data(password2='AnotherPass!23'))
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_weak_password_rejected(self):
        form = RegistrationForm(data=self._data(password1='123', password2='123'))
        self.assertFalse(form.is_valid())


# ---------------------------------------------------------------------------
# Unit-тесты представлений (views)
# ---------------------------------------------------------------------------
class ScheduleViewTest(TestCase):
    """Тесты главной страницы с расписанием"""

    def setUp(self):
        self.doctor = create_doctor()

    def test_page_loads(self):
        response = self.client.get(reverse('schedule'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'schedule.html')

    def test_past_schedules_hidden(self):
        past = create_schedule(self.doctor, days_offset=-1)
        future = create_schedule(self.doctor, days_offset=1)
        response = self.client.get(reverse('schedule'))
        schedules = list(response.context['schedules'])
        self.assertNotIn(past, schedules)
        self.assertIn(future, schedules)

    def test_search_by_doctor_name(self):
        create_schedule(self.doctor)
        response = self.client.get(reverse('schedule'), {'q': 'Иванов'})
        self.assertEqual(len(response.context['schedules']), 1)
        response = self.client.get(reverse('schedule'), {'q': 'Несуществующий'})
        self.assertEqual(len(response.context['schedules']), 0)


class MakeAppointmentViewTest(TestCase):
    """Тесты бизнес-логики записи на приём"""

    def setUp(self):
        self.user = create_user()
        self.client.login(username='patient', password='TestPass123!')
        self.doctor = create_doctor()

    def test_requires_login(self):
        self.client.logout()
        schedule = create_schedule(self.doctor)
        response = self.client.get(reverse('make_appointment', args=[schedule.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_creates_appointment_and_blocks_slot(self):
        schedule = create_schedule(self.doctor, days_offset=1)
        response = self.client.get(reverse('make_appointment', args=[schedule.id]))
        self.assertRedirects(response, reverse('my_appointments'))
        appointment = Appointment.objects.get(patient=self.user, schedule=schedule)
        self.assertEqual(appointment.status, 'pending')
        schedule.refresh_from_db()
        self.assertFalse(schedule.is_available)  # слот занят

    def test_past_schedule_cannot_be_booked(self):
        schedule = create_schedule(self.doctor, days_offset=-1)
        response = self.client.get(reverse('make_appointment', args=[schedule.id]))
        self.assertRedirects(response, reverse('schedule'))
        self.assertFalse(Appointment.objects.filter(schedule=schedule).exists())

    def test_duplicate_appointment_blocked(self):
        schedule = create_schedule(self.doctor, days_offset=1)
        Appointment.objects.create(patient=self.user, schedule=schedule, status='pending')
        response = self.client.get(reverse('make_appointment', args=[schedule.id]))
        self.assertRedirects(response, reverse('schedule'))
        self.assertEqual(Appointment.objects.filter(patient=self.user, schedule=schedule).count(), 1)


class CancelAppointmentViewTest(TestCase):
    """Тесты бизнес-логики отмены записи"""

    def setUp(self):
        self.user = create_user()
        self.client.login(username='patient', password='TestPass123!')
        self.doctor = create_doctor()

    def test_cancel_future_appointment_frees_slot(self):
        schedule = create_schedule(self.doctor, days_offset=1)
        appointment = Appointment.objects.create(patient=self.user, schedule=schedule)
        response = self.client.get(reverse('cancel_appointment', args=[appointment.id]))
        self.assertRedirects(response, reverse('my_appointments'))
        appointment.refresh_from_db()
        schedule.refresh_from_db()
        self.assertEqual(appointment.status, 'cancelled')
        self.assertTrue(schedule.is_available)  # слот освобождён

    def test_cancel_past_appointment_forbidden(self):
        schedule = create_schedule(self.doctor, days_offset=-1, available=False)
        appointment = Appointment.objects.create(patient=self.user, schedule=schedule)

        self.client.get(reverse('cancel_appointment', args=[appointment.id]))

        # Assert: статус не изменился и слот НЕ освобождён
        appointment.refresh_from_db()
        schedule.refresh_from_db()
        self.assertEqual(appointment.status, 'pending')
        self.assertFalse(schedule.is_available)

    def test_cancel_already_cancelled_forbidden(self):
        schedule = create_schedule(self.doctor, days_offset=1, available=False)
        appointment = Appointment.objects.create(patient=self.user, schedule=schedule, status='cancelled')
        self.client.get(reverse('cancel_appointment', args=[appointment.id]))
        schedule.refresh_from_db()
        self.assertEqual(appointment.status, 'cancelled')
        self.assertFalse(schedule.is_available)  # слот не освобождается повторно

    def test_cannot_cancel_other_users_appointment(self):
        other = create_user(username='other', email='other@mail.ru')
        schedule = create_schedule(self.doctor)
        appointment = Appointment.objects.create(patient=other, schedule=schedule)
        response = self.client.get(reverse('cancel_appointment', args=[appointment.id]))
        self.assertEqual(response.status_code, 404)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'pending')


class MyAppointmentsViewTest(TestCase):
    """Тесты личного кабинета и авто-завершения записей"""

    def setUp(self):
        self.user = create_user()
        self.client.login(username='patient', password='TestPass123!')
        self.doctor = create_doctor()

    def test_past_appointment_becomes_completed(self):
        schedule = create_schedule(self.doctor, days_offset=-1)
        appointment = Appointment.objects.create(patient=self.user, schedule=schedule, status='confirmed')
        self.client.get(reverse('my_appointments'))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'completed')

    def test_future_appointment_stays_pending(self):
        schedule = create_schedule(self.doctor, days_offset=1)
        appointment = Appointment.objects.create(patient=self.user, schedule=schedule)
        self.client.get(reverse('my_appointments'))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'pending')

    def test_only_own_appointments_shown(self):
        other = create_user(username='other', email='other@mail.ru')
        Appointment.objects.create(patient=self.user, schedule=create_schedule(self.doctor))
        Appointment.objects.create(patient=other, schedule=create_schedule(self.doctor, days_offset=2))
        response = self.client.get(reverse('my_appointments'))
        self.assertEqual(len(response.context['appointments']), 1)


class AdminSmokeTest(TestCase):
    """Дымовые тесты админ-панели (повышают покрытие admin.py)"""

    def setUp(self):
        User.objects.create_superuser('admin', 'admin@mail.ru', 'AdminPass123!')
        self.client.login(username='admin', password='AdminPass123!')

    def test_admin_changelists_load(self):
        for url in ('/admin/appointment/doctor/', '/admin/appointment/schedule/', '/admin/appointment/appointment/'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)