from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

def group_required(*group_names):
    def decorator(view_function):
        @wraps(view_function)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated and request.user.is_administrador:
                return redirect("login")
            elif not request.user.is_authenticated and not request.user.is_administrador:
                return redirect("login_agricultor")
            if request.user.is_superuser or request.user.groups.filter(name__in=group_names).exists():
                return view_function(request, *args, **kwargs)
            messages.error(request, "Você não tem permissão para acessar essa página!")
            if request.user.is_administrador:
                return redirect("login")
            else:
                return redirect('login_agricultor')
        return wrapper
    return decorator