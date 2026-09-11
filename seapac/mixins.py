from django.contrib import messages
from django.shortcuts import redirect

class GroupRequireMixin:
    allowed_groups = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('escolher_tipo')
        if request.user.is_superuser or request.user.groups.filter(name__in=self.allowed_groups).exists():
            return super().dispatch(request, *args, **kwargs)
        messages.error(request, 'Vocẽ não tem permissão para acessar esta página!')
        return redirect('escolher_tipo')