from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import Group
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import (
    LoginForm,
    PerfilTecnicoForm,
    TecnicoFiltroForm,
    TecnicoEditForm,
    AgricultorLoginForm,
    TecnicoCreationForm
)
from .models import Usuario, Tecnico, Agricultor
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import get_object_or_404

def choice_type(request):
    return render(request, 'login/escolher_tipo.html')

def cadastrar_tecnico(request):

    if request.method == "POST":
        form = TecnicoCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            grupo, created = Group.objects.get_or_create(name='TECNICOS')
            user.groups.add(grupo)

            messages.success(
                request, "Cadastro realizado com sucesso! Faça login para continuar."
            )
            return redirect("login_tecnico")
    else:
        form = TecnicoCreationForm()

    return render(request, "login/cadastrar.html", {"form": form})

def login_agricultor(request):
    if request.user.is_authenticated:
        if request.user.is_agricultor:
            return redirect('dashboard_agricultor')

    if request.method == 'POST':
        form = AgricultorLoginForm(request, data=request.POST)

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request=request, username=username, password=password)

            if user is not None:
                login(request, user)

                if hasattr(user, 'agricultor') and user.agricultor.primeiro_acesso:
                    return redirect('alterar_senha_agricultor')

                messages.success(
                    request, f'Seja bem-vindo ao Sistema SEAPAC'
                )

                next_url = request.GET.get("next")
                if next_url and request.user.groups.filter(
                    name__in=["AGRICULTORES"]).exists():
                    return redirect(next_url)

                return redirect("dashboard_agricultor")
        else:
            messages.error(request, "Usuário ou senha inválidos.")
    else:
        form = AgricultorLoginForm()

    return render(request, "login/login_agricultor.html", {"form": form})

def alterar_senha_agricultor(request):
    agricultor = request.user.agricultor

    if not agricultor.primeiro_acesso:
        return redirect('dashboard_agricultor')

    if request.method == 'POST':
        form = SetPasswordForm(request.user, request.POST)

        if form.is_valid():
            user = form.save()

            update_session_auth_hash(request, user)

            Agricultor.objects.filter(
                pk=agricultor.pk
            ).update(
                primeiro_acesso=False
            )

            return redirect('dashboard_agricultor')

    else:
        form = SetPasswordForm(request.user)

    return render(request, 'login/alterar_senha_agricultor.html', {'form': form}
    )

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_tecnico:
            return redirect("dashboard")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(
                    request, f"Bem-vindo ao Sistema SEAPAC, {user.username}!"
                )

                next_url = request.GET.get("next")
                if next_url and request.user.groups.filter(
                    name__in=["TECNICOS"]).exists():
                    return redirect(next_url)

                return redirect("dashboard")

        else:
            messages.error(request, "Usuário ou senha inválidos.")
    else:
        form = LoginForm()

    return render(request, "login/login.html", {"form": form})


@require_POST
def logout_view(request):
    request.session.flush()
    messages.info(request, "Você saiu do sistema.")
    return redirect("index")


@never_cache
@login_required
def perfil_view(request):
    if request.user.is_tecnico:
        user = get_object_or_404(Tecnico, pk=request.user.pk)
        formClass = PerfilTecnicoForm

    if request.method == "POST":
        form = formClass(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado com sucesso!")
            return redirect("perfil")
    else:
        form = formClass(instance=user)

    return render(request, "login/perfil.html", {"form": form, "user": user})


def index(request):
    return render(request, "homepage/index.html")


@never_cache
@login_required
def list_user(request):
    if not request.user.is_administrador and not request.user.is_superuser:
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect("dashboard")

    usuarios = Tecnico.objects.all().order_by("-date_joined")

    filtro_form = TecnicoFiltroForm(request.GET or None)

    if filtro_form.is_valid():

        username = filtro_form.cleaned_data.get("username")
        if username:
            usuarios = usuarios.filter(username__icontains=username)

        email = filtro_form.cleaned_data.get("email")
        if email:
            usuarios = usuarios.filter(email__icontains=email)

        cpf = filtro_form.cleaned_data.get("cpf")
        if cpf:
            usuarios = usuarios.filter(cpf__icontains=cpf)

        nome_cidade = filtro_form.cleaned_data.get("cidade")
        if nome_cidade:
            usuarios = usuarios.filter(nome_cidade__icontains=nome_cidade)

        grupo = filtro_form.cleaned_data.get("grupo")
        if grupo:
            usuarios = usuarios.filter(groups=grupo)

        is_active = filtro_form.cleaned_data.get("is_active")
        if is_active == "true":
            usuarios = usuarios.filter(is_active=True)
        elif is_active == "false":
            usuarios = usuarios.filter(is_active=False)

    itens_por_pagina = 10
    paginator = Paginator(usuarios, itens_por_pagina)
    page_number = request.GET.get("page")

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    return render(
        request,
        "painel/list_user.html",
        {
            "usuarios": page_obj,
            "page_obj": page_obj,
            "filtro_form": filtro_form,
        },
    )


@login_required
def criar_usuario_admin(request):
    if not request.user.is_administrador and not request.user.is_superuser:
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect("dashboard")

    if request.method == "POST":
        form = TecnicoCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            grupo_simples, created = Group.objects.get_or_create(name="TECNICOS")
            user.groups.add(grupo_simples)

            messages.success(request, f"Usuário {user.username} criado com sucesso!")
            return redirect("list_user")
    else:
        form = TecnicoCreationForm()

    return render(
        request, "painel/form_user.html", {"form": form, "titulo": "Criar Novo Usuário"}
    )


@login_required
def editar_usuario_admin(request, pk):

    if not request.user.is_administrador and not request.user.is_superuser:
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect("list_user")

    usuario = get_object_or_404(Tecnico, pk=pk)

    if request.method == "POST":
        form = TecnicoEditForm(request.POST, request.FILES, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(
                request, f"Usuário {usuario.username} atualizado com sucesso!"
            )
            return redirect("list_user")
    else:
        form = TecnicoEditForm(instance=usuario)

    return render(
        request,
        "painel/form_user.html",
        {
            "form": form,
            "titulo": f"Editar Usuário: {usuario.username}",
            "usuario": usuario,
            "tipo": "edit",
        },
    )


@login_required
def deletar_usuario(request, pk):

    if not request.user.is_administrador and not request.user.is_superuser:
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect("list_user")

    usuario = get_object_or_404(Tecnico, pk=pk)

    if usuario == request.user:
        messages.error(request, "Você não pode deletar seu próprio usuário!")
        return redirect("list_user")

    if usuario.is_superuser:
        messages.error(request, "Não é possível deletar um superusuário!")
        return redirect("list_user")

    if request.method == "POST":
        username = usuario.username
        usuario.delete()
        messages.success(request, f"Usuário {username} deletado com sucesso!")
        return redirect("list_user")

    return render(request, "painel/confirmar_delete_usuario.html", {"usuario": usuario})
