from .models import Doctor


def user_role(request):
    """
    Определяет роль текущего пользователя (врач/пациент)
    и передаёт флаги во все шаблоны.
    """
    if request.user.is_authenticated:
        is_doctor = Doctor.objects.filter(user=request.user).exists()
        doctors = Doctor.objects.filter(user=request.user) if is_doctor else []
    else:
        is_doctor = False
        doctors = []

    return {
        'is_doctor': is_doctor,
        'user_doctors': doctors,
    }