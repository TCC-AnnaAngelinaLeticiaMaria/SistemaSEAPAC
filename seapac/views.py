from .models import (
    Family,
    Subsystem,
    Evento,
    Project,
    Technician,
    FamilySubsystem,
    TimelineEvent,
    Municipality,
    Evento,
    FamilyRenda,
    Community,
    currentyear,
)
from .forms import (
    FamilyForm,
    ProjectForm,
    TechnicianForm,
    SubsystemForm,
    TimelineEventForm,
    FluxoForm,
    BaseFluxoFormSet,
    FamilyEditForm,
    ProjectEditForm,
    TechnicianEditForm,
    SubsystemEditForm,
    TimelineEventEditForm,
    ImportarPlanilha,
)
from usuarios.models import Agricultor
from django.contrib.auth.models import Group
from usuarios.decorators import group_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from .reports.pdf import gerar_relatorio_family
from django.core.paginator import Paginator
from .mixins import GroupRequireMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.staticfiles import finders
from django.http import HttpResponse, HttpResponseBadRequest
from django.forms import formset_factory
from django.http import FileResponse
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.views import View
from django.db import transaction
from weasyprint import HTML, CSS
import pandas as pd
import unicodedata
import secrets
import openpyxl
import re

import json

#**********************************
#*************TÉCNICOS*************
#**********************************

LEVEL_CHOICES = [(1, "Inicial"), (2, "Intermediario"), (3, "Avancado")]

# --------------DASHBOARD--------------
@never_cache
@login_required
@group_required('TECNICOS')
def dashboard(request):
    level = request.GET.get("nivel")
    query = request.GET.get("q")
    families = Family.objects.all()
    if query:
        families = families.filter(nome_titular__icontains=query)
    
    total_municipios = (
        Municipality.objects.filter(family__isnull=False).distinct().count()
    )
    total_families = Family.objects.count()
    total_tecnicos = Technician.objects.count()
#    total_avancado = len(
#        [f for f in Family.objects.all() if f.get_nivel() == "Avancado"]
#    )
#    total_intermediario = len(
#        [f for f in Family.objects.all() if f.get_nivel() == "Intermediario"]
#    )
#    total_inicial = len([f for f in Family.objects.all() if f.get_nivel() == "Inicial"])
    total_visitas = Evento.objects.count()

    context = {
        "families": families,
        "total_families": total_families,
        "title": "Página Inicial - Dashboard",
        "query": query,
        "total_municipios": total_municipios,
        "total_visitas": total_visitas,
        "total_tecnicos": total_tecnicos,
    }
    return render(request, "seapac/dashboard.html", context)


# --------------CRUD FAMILIAS (COMPLETO)--------------

def normalizarColunas(coluna_nome):
        coluna_nome = str(coluna_nome).strip().lower()

        coluna_nome = unicodedata.normalize('NFKD', coluna_nome)
        coluna_nome = ''.join(caractere for caractere in coluna_nome if not unicodedata.combining(caractere))

        return ' '.join(coluna_nome.split())

def normalizar_contato(contato):
    if pd.isna(contato):
        return None

    contato = str(contato).strip()

    if contato.endswith(".0"):
        contato = contato[:-2]

    contato = re.sub(r"\D", "", contato)

    if not contato:
        return None

    if len(contato) != 11:
        return None

    return contato

def verificarCampos(dataFrame, campos):
    colunas = {}

    for coluna in dataFrame.columns:
        colunas[normalizarColunas(coluna)] = coluna

    for campo in campos:
        campo = normalizarColunas(campo)
        if campo in colunas:
            return colunas[campo]

    return None

class ImportarDadosExcel(LoginRequiredMixin, GroupRequireMixin, View):
    allowed_groups = ['TECNICOS']

    def get(self, request):
        familia = Family.objects.all()
        form =  ImportarPlanilha()
        return render(request, "seapac/familias/importardados.html", {'form': form, 'familia': familia})

    def post(self, request):

        form = ImportarPlanilha(request.POST, request.FILES)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Informações de login das famílias'

        ws.append(['Nome do Titular', 'Contato', 'Senha'])

        if form.is_valid():
            arq = request.FILES['arquivo']
            dataFrame = pd.read_excel(arq)

            campo_nome = verificarCampos(dataFrame, ['Nome Completo', 'Nome', 'Nome do Titular'])

            campo_contato = verificarCampos(dataFrame, ['Telefone', 'Celular', 'Contato'])

            campo_municipio = verificarCampos(dataFrame, ['Município', 'Municipio'])

            with transaction.atomic():

                for _, row in dataFrame.iterrows():

                    contato = normalizar_contato(row[campo_contato])

                    municipio, created1 = Municipality.objects.get_or_create(
                        nome=row[campo_municipio]
                    )

                    comunidade, created2 = Community.objects.get_or_create(
                        nome_comunidade=row['Comunidade'],
                        municipio=municipio,
                    )

                    familia, created3 = Family.objects.get_or_create(
                        nome_titular= row[campo_nome],
                        municipio= municipio, 
                        defaults={
                            'contato': contato,
                            'comunidade': comunidade,
                        }
                    )

                    if created3 and familia.contato:
                        senha_temporaria = secrets.token_urlsafe(8)
                        agricultor = Agricultor.objects.create_user(
                            username=familia.contato,
                            password=senha_temporaria,
                            familia=familia
                        )
            
                        grupo, _ = Group.objects.get_or_create(name='AGRICULTORES')
                        agricultor.groups.add(grupo)

                        ws.append([familia.nome_titular, familia.contato, senha_temporaria])

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename=Credenciais_temporarias_agricultores.xlsx'

            wb.save(response)

            return response
        return render(request, "seapac/familias/importardados.html", {'form': form})


@never_cache
@login_required
@group_required('TECNICOS')
def register(request):

    if request.method == "POST":
        form = FamilyForm(request.POST, request.FILES)
        if form.is_valid():

            with transaction.atomic():
                family = form.save(commit=False)
                family.save()

                senha_temporaria = secrets.token_urlsafe(8)
                agricultor = Agricultor.objects.create_user(
                    username=family.contato,
                    password=senha_temporaria,
                    familia=family
                )

                grupo, _ = Group.objects.get_or_create(name='AGRICULTORES')
                agricultor.groups.add(grupo)

            return render(
                request,
                "seapac/info_cadastro_agricultor.html",
                {
                    "familia": family,
                    "senha_temporaria": senha_temporaria,
                }
            )
    else:
        form = FamilyForm()
    return render(
        request,
        "seapac/familias/form.html",
        {"form": form, "title": "Cadastrar Família"},
    )


@never_cache
@login_required
@group_required('TECNICOS', 'AGRICULTORES')
def detail_family(request, id):
    family = get_object_or_404(Family, id=id)
    context = {"family": family, "title": "Detalhes da "}
    return render(request, "seapac/familias/detail_family.html", context)


@never_cache
@login_required
@group_required('TECNICOS')
def edit_family(request, id):
    family = get_object_or_404(Family, id=id)

    if request.method == "POST":
        form = FamilyEditForm(request.POST, request.FILES, instance=family)
        if form.is_valid():
            form.save()
            return redirect("dashboard")
    else:
        form = FamilyEditForm(instance=family)
    return render(
        request, "seapac/familias/form.html", {"form": form, "title": "Editar Família"}
    )


@never_cache
@login_required
@group_required('TECNICOS')
def list_families(request):
    # level = request.GET.get("nivel")
    query = request.GET.get("q")
    subsystem_name = request.GET.get("subsystem")

    families = Family.objects.all()

    if query:
        families = families.filter(nome_titular__icontains=query)

    if subsystem_name:
        families = families.filter(
            familyrenda__familysubsystem__subsystem__nome_subsistema=subsystem_name
        ).distinct()


    paginator = Paginator(families, 4)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    page_range = paginator.get_elided_page_range(number=page_obj.number, on_each_side=1, on_ends=2)

    subsystems = Subsystem.objects.all()

    context = {
        "title": "Lista de Famílias",
    #    "nivel_selecionado": level,
        "query": query,
        "page_obj": page_obj,
        "families": page_obj,
        "subsystems": subsystems,
        "subsystem_selected": subsystem_name,
        "objeto": "familias",
        "families_list": families,
        'page_range': page_range,
    }
    return render(request, "seapac/familias/list_families.html", context)


@never_cache
@login_required
@group_required('TECNICOS')
def delete_family(request, id):
    family = get_object_or_404(Family, id=id)
    family.delete()
    messages.success(
        request, f'A família "{family.get_nome_familia}" foi excluída com sucesso!'
    )
    return redirect("dashboard")


# --------------RENDA FAMILIAR--------------


@never_cache
@login_required
@group_required('TECNICOS', 'AGRICULTORES')
def renda_familiar_detail(request, id, ano):
    family = get_object_or_404(Family, id=id)
    renda = get_object_or_404(FamilyRenda, family=family, ano=ano)
    resultado = renda.calcular_renda()

    context = {
        "family": family,
        "ano": ano,
        "produtos": resultado["produtos"],
        "total_receita": resultado["total_receita"],
        "total_custo": resultado["total_custo"],
        "renda_total": resultado["renda_total"],
        "total_receita_potencial": resultado["total_receita_potencial"],
        "renda_total_potencial": resultado["renda_total_potencial"],
        "title": f"Renda da ",
        "diferenca": resultado["diferenca"],
    }
    return render(request, "seapac/familias/renda_familiar_detail.html", context)
    
# --------------CRUD PROJETOS (COMPLETO)------------------
@never_cache
@login_required
@group_required('TECNICOS')
def list_projects(request):
    status = request.GET.get("status")
    query = request.GET.get("q")

    projects = Project.objects.all()
    if status:
        projects = projects.filter(status=status)
    if query:
        projects = projects.filter(nome_projeto__icontains=query)

    paginator = Paginator(projects, 3)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "query": query,
        "page_obj": page_obj,
        "projects": page_obj,
        "objeto": "projetos",
        "status": status,
    }
    return render(request, "seapac/projetos/projects.html", context)


@never_cache
@login_required
@group_required('TECNICOS')
def create_projects(request):
    if request.method == "POST":
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("list_projects")
    else:
        form = ProjectForm()

    return render(
        request,
        "seapac/projetos/projects_form.html",
        {"form": form, "title": "Cadastrar Projeto"},
    )


@never_cache
@login_required
@group_required('TECNICOS')
def edit_projects(request, pk):
    projetos = get_object_or_404(Project, pk=pk)

    if request.method == "POST":
        form = ProjectEditForm(request.POST, instance=projetos)
        if form.is_valid():
            form.save()
            return redirect("detail_projects", pk=projetos.pk)
    else:
        form = ProjectEditForm(instance=projetos)

    return render(
        request,
        "seapac/projetos/projects_form.html",
        {"form": form, "projetos": projetos, "title": "Editar Projeto"},
    )


@never_cache
@login_required
@group_required('TECNICOS')
def detail_projects(request, pk):
    projetos = get_object_or_404(Project, pk=pk)
    context = {"projetos": projetos}
    return render(request, "seapac/projetos/projects_detail.html", context)


@never_cache
@login_required
@group_required('TECNICOS')
def delete_projects(request, pk):
    projetos = get_object_or_404(Project, pk=pk)
    projetos.delete()
    messages.success(
        request, f'O projeto "{projetos.nome_projeto}" foi excluído com sucesso!'
    )
    return redirect("list_projects")


# --------------CRUD TECNICOS (COMPLETO)--------------
@never_cache
@login_required
@group_required('TECNICOS')
def list_tecs(request):
    especialidade = request.GET.get("especialidade")
    query = request.GET.get("q")

    tecs = Technician.objects.all()
    if especialidade:
        tecs = tecs.filter(especialidade=especialidade)
    if query:
        tecs = tecs.filter(nome_tecnico__icontains=query)

    paginator = Paginator(tecs, 3)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "page_obj": page_obj,
        "tecs": page_obj,
        "objeto": "técnicos",
        "especialidade": especialidade,
    }
    return render(request, "seapac/tecnicos/tecnicos.html", context)


@never_cache
@login_required
@group_required('TECNICOS')
def create_tecs(request):
    if request.method == "POST":
        form = TechnicianForm(request.POST)
        if form.is_valid():
            tecs = form.save()
            return redirect("list_tecs")

    else:
        form = TechnicianForm()

    return render(
        request,
        "seapac/tecnicos/tecnicos_form.html",
        {"form": form, "title": "Cadastrar Técnico"},
    )


@never_cache
@login_required
@group_required('TECNICOS')
def edit_tecs(request, pk):
    tecs = get_object_or_404(Technician, pk=pk)

    if request.method == "POST":
        form = TechnicianEditForm(request.POST, instance=tecs)
        if form.is_valid():
            form.save()
            return redirect("detail_tecs", pk=tecs.pk)
    else:
        form = TechnicianEditForm(instance=tecs)

    return render(
        request,
        "seapac/tecnicos/tecnicos_form.html",
        {"form": form, "tecs": tecs, "title": "Editar Técnico"},
    )


@never_cache
@login_required
@group_required('TECNICOS')
def detail_tecs(request, pk):
    tecs = get_object_or_404(Technician, pk=pk)
    context = {"tecs": tecs}
    return render(request, "seapac/tecnicos/tecnicos_detail.html", context)


@never_cache
@login_required
@group_required('TECNICOS')
def delete_tecs(request, pk):
    tecs = get_object_or_404(Technician, pk=pk)
    tecs.delete()
    messages.success(request, f"Técnico {tecs.nome_tecnico} excluído com sucesso!")
    return redirect("list_tecs")


# --------------CRUD SUBSISTEMAS (COMPLETO)--------------


@never_cache
@login_required
@group_required('TECNICOS')
def list_subsystems(request):
    query = request.GET.get("q")
    subsistemas = Subsystem.objects.all()
    if query:
        subsistemas = subsistemas.filter(nome_subsistema__icontains=query)
    context = {
        "subsistemas": subsistemas,
        "title": "Lista de Subsistemas",
        "query": query,
    }
    return render(request, "seapac/subsistemas/list_subsystems.html", context)


@never_cache
@login_required
@group_required('TECNICOS', 'AGRICULTORES')
def detail_subsystems(request, id):
    subsistema = get_object_or_404(Subsystem, id=id)
    context = {"subsistema": subsistema, "title": "Detalhes do Subsistema"}
    return render(request, "seapac/subsistemas/subsystem_detail.html", context)


@never_cache
@login_required
@group_required('TECNICOS')
def create_subsystems(request):
    if request.method == "POST":
        form = SubsystemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("list_subsystems")
    else:
        form = SubsystemForm()

    return render(
        request,
        "seapac/subsistemas/subsystem_form.html",
        {"form": form, "title": "Cadastrar Subsistema"},
    )


@never_cache
@login_required
@group_required('TECNICOS')
def edit_subsystems(request, id):
    subsistema = get_object_or_404(Subsystem, id=id)

    if request.method == "POST":
        form = SubsystemEditForm(request.POST, request.FILES, instance=subsistema)
        if form.is_valid():
            form.save()
            return redirect("list_subsystems")
    else:
        form_data = "\n".join([p.get("nome", "") for p in subsistema.produtos_base])
        form = SubsystemEditForm(
            instance=subsistema, initial={"produtos_base": form_data}
        )

    return render(
        request,
        "seapac/subsistemas/subsystem_form.html",
        {"title": "Editar Subsistema", "form": form, "subsistema": subsistema},
    )


@never_cache
@login_required
@group_required('TECNICOS')
def delete_subsystems(request, id):
    subsistema = get_object_or_404(Subsystem, id=id)
    subsistema.delete()
    messages.success(
        request, f'Subsistema "{subsistema.nome_subsistema}" excluído com sucesso!'
    )
    return redirect("list_subsystems")


# --------------CRUD FLUXO+SUBSISTEMAS--------------
@never_cache
@login_required
@group_required('TECNICOS')
def flow(request, id, ano):
    family = get_object_or_404(Family, id=id)
    renda_ano = get_object_or_404(FamilyRenda, family=family, ano=ano)
    family_subsystems = FamilySubsystem.objects.filter(family_renda=renda_ano).select_related(
        "subsystem"
    )
    style_mode = request.GET.get("style", "default")

    subsystems_data = []
    for family_subsystem in family_subsystems:
        subsystems_data.append(
            {
                "id": family_subsystem.subsystem.id,
                "nome_subsistema": family_subsystem.subsystem.nome_subsistema,
                "tipo": family_subsystem.subsystem.tipo,
                "produtos_saida": family_subsystem.produtos_saida,
            }
        )

    fluxos = []
    for subsystem in subsystems_data:
        nome_subsistema = subsystem["nome_subsistema"]
        for produto in subsystem["produtos_saida"]:
            nome_produto = produto["nome"]
            fluxos_do_produto = produto.get("fluxos", [])

            total_qtd = sum((f.get("qtd") or 0) for f in fluxos_do_produto)

            for fluxo in fluxos_do_produto:
                destino = fluxo.get("destino", "Mundo Externo")
                qtd = fluxo.get("qtd")
                und = fluxo.get("und", "")
                porcentagem_calc = round((qtd / total_qtd) * 100, 1) if total_qtd else 0

                rotulo_fluxo = nome_produto
                if qtd:
                    rotulo_fluxo += f" {qtd}"
                if und:
                    rotulo_fluxo += f" {und}"
                if porcentagem_calc:
                    rotulo_fluxo += f" {porcentagem_calc:.0f}%"

                fluxos.append((nome_subsistema, rotulo_fluxo, destino))

    text_list = []
    if style_mode == "notext":
        for origem, _, destino in fluxos:
            origem_corrigida = origem.replace(" ", "_")
            destino_corrigida = destino.replace(" ", "_")
            text_list.append(f"{origem_corrigida} --> {destino_corrigida}")
    else:
        for origem, produto, destino in fluxos:
            origem_corrigida = origem.replace(" ", "_")
            destino_corrigida = destino.replace(" ", "_")
            text_list.append(f"{origem_corrigida} --{produto}--> {destino_corrigida}")

    flux_count = {}
    for origem, produto, destino in fluxos:
        flux_count[origem] = flux_count.get(origem, 0) + 1

    subsystems_com_fluxo = {nome for fluxo in fluxos for nome in (fluxo[0], fluxo[2])}

    subsystems_sem_fluxo = [
        s["nome_subsistema"].replace(" ", "_")
        for s in subsystems_data
        if s["nome_subsistema"] not in subsystems_com_fluxo
    ]

    click_lines = []
    for s in subsystems_data:
        subsystem_id = s["id"]
        nome_subsistema = s["nome_subsistema"].replace(" ", "_")
        host = request.get_host()
        if ":" not in host:
            host = f"{host}:82"
        url = f"{request.scheme}://{host}{reverse('subsystem_panel', args=[family.id, subsystem_id, renda_ano.id])}"
        click_lines.append(
            f'click {nome_subsistema} href "{url}" "Abrir painel de {nome_subsistema}"'
        )

    for nome in subsystems_sem_fluxo:
        text_list.append(f"{nome}")

    def get_color_intensity(n, tipo):
        if tipo == "TS":
            if n <= 2:
                return "#b7d8f5"
            elif n <= 5:
                return "#6eb5e7"
            elif n <= 9:
                return "#3690c2"
            else:
                return "#125877"
        elif tipo == "ME":
            if n <= 2:
                return "#f7d26a"
            elif n <= 5:
                return "#f5b900"
            elif n <= 9:
                return "#c48f00"
            else:
                return "#7a5e00"
        else:
            if n <= 2:
                return "#b7f5b7"
            elif n <= 5:
                return "#6ee76e"
            elif n <= 9:
                return "#36c236"
            else:
                return "#127712"

    classDefSS = "classDef cssFlowSS stroke:#333,stroke-width:1px;"
    classDefTS = "classDef cssFlowTS stroke:#333,stroke-width:1px;"

    style_lines = []
    for s in subsystems_data:
        nome = s["nome_subsistema"].replace(" ", "_")
        tipo = s.get("tipo", "SS")
        n_fluxos = flux_count.get(s["nome_subsistema"], 0)
        fill_color = get_color_intensity(n_fluxos, tipo)
        style_lines.append(
            f"style {nome} fill:{fill_color},stroke:#333,stroke-width:1px;"
        )

    me_nodes = [
        s["nome_subsistema"].replace(" ", "_")
        for s in subsystems_data
        if s["tipo"] == "ME"
    ]
    if me_nodes:
        mundo_externo = "subgraph Mundo Externo\n"
        for node in me_nodes:
            mundo_externo += f"    {node}\n"
        mundo_externo += "end"
    else:
        mundo_externo = ""

    diagram_lines = "\n".join(text_list)
    style_lines_str = "\n".join(style_lines)
    click_lines_str = "\n".join(click_lines)

    conteudo_mermaid = f"""flowchart LR
{mundo_externo}

{classDefSS}
{classDefTS}
{diagram_lines}

{click_lines_str}

{style_lines_str}
"""
    context = {
        "id": id,
        "family": family,
        "family_subsystems": family_subsystems,
        "style_mode": style_mode,
        "title": "Fluxo",
        "conteudo_mermaid": conteudo_mermaid,
        'ano': ano
    }
    return render(request, "seapac/flow.html", context)

@never_cache
@login_required
@group_required('TECNICOS')
def flow_list(request, id):
    current_year = currentyear()

    family = get_object_or_404(Family, id=id)
    rendas = FamilyRenda.objects.filter(family=family).order_by("-ano")
    
    return render(request, 'seapac/flowlist.html', {'family': family, 'rendas': rendas, 'anos': range(1993, current_year+1), 'title': 'Fuxogramas da'})

@never_cache
@login_required
@group_required('TECNICOS')
def subsystem_panel(request, family_id, subsystem_id, renda_id):
    family = get_object_or_404(Family, id=family_id)
    family_renda = get_object_or_404(FamilyRenda, family=family, id=renda_id)
    family_subsystem = get_object_or_404(
        FamilySubsystem, subsystem_id=subsystem_id, family_renda=family_renda
    )

    for produto in family_subsystem.produtos_saida:
        fluxos = produto.get("fluxos", [])
        total_qtd = sum(f.get("qtd", 0) or 0 for f in fluxos)
        for fluxo in fluxos:
            qtd = fluxo.get("qtd", 0) or 0
            fluxo["porcentagem_calc"] = (
                round((qtd / total_qtd) * 100, 2) if total_qtd else 0
            )

    if not family_subsystem.produtos_saida:
        family_subsystem.produtos_saida = family_subsystem.subsystem.produtos_base
        family_subsystem.save()

    return render(
        request,
        "seapac/subsystem_panel.html",
        {
            "subsystem": family_subsystem.subsystem,
            "family": family,
            "family_subsystem": family_subsystem,
            "title": "Painel do Subsistema",
            "type": "readonly",
            "renda_ano": family_renda
        },
    )

@never_cache
@login_required
@group_required('TECNICOS')
def new_subsystem_to_family(request, id, ano):
    current_year = currentyear()

    if not (1993 <= ano <= current_year):
        return HttpResponseBadRequest("Ano inválido")

    family = get_object_or_404(Family, id=id)

    renda_ano, criada = FamilyRenda.objects.get_or_create(
        family=family,
        ano=ano
    )
    if request.method == 'POST':
        subsystem_choice = request.POST.getlist('subsistemas')

        for subsystem_id in subsystem_choice:
            subsystem = get_object_or_404(Subsystem, id=subsystem_id)
            renda_ano.add_subsystem_to_family(subsystem)   

        return redirect('flow_list', id=family.id)

    subsys_vinculados_ids = FamilySubsystem.objects.filter(
        family_renda = renda_ano
    ).values_list('subsystem_id', flat=True)

    subsystems = Subsystem.objects.all()
    
    return render(request, 'seapac/formflow.html', {
        'family': family,
        'ano': ano,
        'renda_ano': renda_ano,
        'subsystems': subsystems,
        'selected_ids': list(subsys_vinculados_ids),
    })

@never_cache
@login_required
@group_required('TECNICOS')
def edit_subsystem_panel(request, family_id, subsystem_id, renda_id):
    family = get_object_or_404(Family, id=family_id)
    family_renda = get_object_or_404(FamilyRenda, family=family, id=renda_id)
    family_subsystem = get_object_or_404(
        FamilySubsystem, subsystem_id=subsystem_id, family_renda=family_renda
    )

    subsystems_destino = Subsystem.objects.filter(
    familysubsystem__family_renda=family_renda).distinct()

    destino_choices = [
        (s.nome_subsistema, s.nome_subsistema) for s in subsystems_destino
    ]
    destino_choices.insert(0, ("", "---------"))

    produto_choices = [(p["nome"], p["nome"]) for p in family_subsystem.produtos_saida]

    FluxoFormSet = formset_factory(
        FluxoForm, formset=BaseFluxoFormSet, extra=1, can_delete=True
    )

    if request.method == "POST":
        formset = FluxoFormSet(request.POST, prefix="fluxo")

        for form in formset:
            form.fields["nome_produto"].choices = produto_choices
            form.fields["destino"].choices = destino_choices

        if formset.is_valid():
            produtos_saida_atualizados = list(family_subsystem.produtos_saida)
            novos_fluxos = {p["nome"]: [] for p in produtos_saida_atualizados}

            for form in formset:
                if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                    continue

                nome_produto = form.cleaned_data["nome_produto"]
                novos_fluxos[nome_produto].append(
                    {
                        "qtd": float(form.cleaned_data.get("qtd") or 0),
                        "custo": float(form.cleaned_data.get("custo") or 0),
                        "und": form.cleaned_data.get("und") or "",
                        "valor": float(form.cleaned_data.get("valor") or 0),
                        "valor_potencial": float(
                            form.cleaned_data.get("valor_potencial") or 0
                        ),
                        "porcentagem": float(form.cleaned_data.get("porcentagem") or 0),
                        "destino": form.cleaned_data.get("destino") or "",
                    }
                )

            for produto in produtos_saida_atualizados:
                nome = produto["nome"]
                produto["fluxos"] = novos_fluxos.get(nome, [])

            family_subsystem.produtos_saida = produtos_saida_atualizados
            family_subsystem.save()

            return redirect(
                "subsystem_panel",
                family_id=family.id,
                subsystem_id=family_subsystem.subsystem.id,
                renda_id=renda_id,
            )

    else:
        initial_data = []
        for produto in family_subsystem.produtos_saida:
            if produto["fluxos"]:
                for fluxo in produto["fluxos"]:
                    initial_data.append(
                        {
                            "nome_produto": produto["nome"],
                            "qtd": fluxo.get("qtd", ""),
                            "und": fluxo.get("und", ""),
                            "custo": fluxo.get("custo", ""),
                            "valor": fluxo.get("valor", ""),
                            "valor_potencial": fluxo.get("valor_potencial", ""),
                            "porcentagem": fluxo.get("porcentagem", ""),
                            "destino": fluxo.get("destino", ""),
                        }
                    )

        formset = FluxoFormSet(initial=initial_data, prefix="fluxo")

        for form in formset:
            form.fields["nome_produto"].choices = produto_choices
            form.fields["destino"].choices = destino_choices

    return render(
        request,
        "seapac/subsystem_panel.html",
        {
            "subsystem": family_subsystem.subsystem,
            "family": family,
            "family_subsystem": family_subsystem,
            "title": "Editar Painel do Subsistema",
            "type": "edit",
            "formset": formset,
            "renda_ano": family_renda
        },
    )


# --------------CRUD TIMELINE--------------


@never_cache
@login_required
@group_required('TECNICOS', 'AGRICULTORES')
def timeline(request, id):
    family = get_object_or_404(Family, id=id)
    timeline_events = family.timeline_events.all().order_by("data", "id")

#    secoes = {}
#    for evento in timeline_events:
#        if evento.secao not in secoes:
#            secoes[evento.secao] = []
#        secoes[evento.secao].append(evento)

#    conteudo_mermaid = "timeline\n"
#    for secao, eventos in secoes.items():
#        conteudo_mermaid += f"    section {secao}\n"
#        for evento in eventos:
#            conteudo_mermaid += (
#                f"        {evento.data} : {evento.titulo} - {evento.descricao}\n"
#            )

    context = {
        "id": id,
        "family": family,
        "events": timeline_events,
        "title": "Linha do Tempo",
#        "conteudo_mermaid": conteudo_mermaid,
    }
    return render(request, "seapac/timeline/timeline.html", context)


@never_cache
@login_required
@group_required('TECNICOS')
def add_timeline(request, id):
    family = get_object_or_404(Family, id=id)
    timeline_events = family.timeline_events.all().order_by("data")

    if request.method == "POST":
        form = TimelineEventForm(request.POST)
        if form.is_valid():
            timeline_event = form.save(commit=False)
            timeline_event.family = family
            timeline_event.save()
            return redirect("timeline", id=family.id)
    else:
        form = TimelineEventForm()

    return render(
        request,
        "seapac/timeline/form_timeline.html",
        {"form": form, "title": "Adicionar Evento à Timeline", "family": family},
    )

@never_cache
@login_required
@group_required('TECNICOS')
def delete_timeline(request, id, event_id):
    family = get_object_or_404(Family, id=id)
    evento = get_object_or_404(TimelineEvent, id=event_id, family=family)

    if request.method == 'POST':
        evento.delete()

    return redirect('timeline', id=id)


@never_cache
@login_required
@group_required('TECNICOS')
def edit_timeline(request, id, event_id):
    family = get_object_or_404(Family, id=id)
    event = get_object_or_404(TimelineEvent, id=event_id, family=family)
    timeline_events = family.timeline_events.all().order_by("data")

    if request.method == "POST":
        form = TimelineEventEditForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect("timeline", id=family.id)
    else:
        form = TimelineEventEditForm(instance=event)

    return render(
        request,
        "seapac/timeline/form_timeline.html",
        {
            "form": form,
            "title": "Editar Evento da Timeline",
            "family": family,
            "timeline_events": timeline_events,
            "event": event,
        },
    )


@never_cache
@login_required
@group_required('TECNICOS')
def search_timeline_event(request, id):
    family = get_object_or_404(Family, id=id)

    if request.method == "POST":
        termo = request.POST.get("termo")
        if termo:
            try:
                evento = family.timeline_events.get(titulo__icontains=termo)
                return redirect("edit_timeline", id=family.id, event_id=evento.id)
            except TimelineEvent.DoesNotExist:
                messages.error(
                    request, f"Nenhum evento encontrado com o título '{termo}'."
                )
        else:
            messages.error(request, "Por favor, digite um título para pesquisar.")

    return redirect("timeline", id=family.id)


# -------------- GERAÇÃO DE RELATÓRIOS/PDFs--------------


@login_required
@group_required('TECNICOS')
def relatorio_family_pdf(request, id):
    family = get_object_or_404(Family, id=id)
    pdf_buffer = gerar_relatorio_family(family)

    return FileResponse(
        pdf_buffer, as_attachment=True, filename=f"relatorio_{family.nome_titular}.pdf"
    )

@login_required
@group_required('TECNICOS')
def pdf_timeline(request, id):
    family = get_object_or_404(Family, id=id)
    eventos = TimelineEvent.objects.filter(family=family).order_by("data", "id")

    html_txt = render(request, 'seapac/timeline/pdf_timeline.html', {'family': family, 'events': eventos}).content.decode("utf-8")
    css_path = finders.find('css/timeline_pdf.css')
    pdf = HTML(string=html_txt, base_url=request.build_absolute_uri('/')).write_pdf(stylesheets=[CSS(filename=css_path)])

    response = HttpResponse(
        pdf,
        content_type='application/pdf',
    )
    response['Content-Disposition'] = (
        f'attachment; filename="timeline{family.nome_titular}.pdf"'
    )

    return response

#------------------------------------------------------------------------

#**********************************
#***********AGRICULTORES***********
#**********************************

@never_cache
@login_required
@group_required('AGRICULTORES')
def dashboard_agricultores(request):
    family = get_object_or_404(Family, agricultor=request.user)
    context = {
        "title": "Página Inicial",
        "family": family,
    }
    return render(request, "seapac/agricultores/dashboard_agricultor.html", context)

@never_cache
@login_required
@group_required('AGRICULTORES')
def list_flows_agricultor(request):
    family = get_object_or_404(Family, agricultor=request.user)
    rendas = FamilyRenda.objects.filter(family=family).order_by("-ano")
    
    context = {
        "title": "Fluxos",
        'rendas': rendas,
        'family': family
    }
    return render(request, "seapac/agricultores/list_flow_agricultor.html", context)

@never_cache
@login_required
@group_required('AGRICULTORES')
def flow_agricultor(request, id, ano):
    
    context = {
        "title": "Fluxos",
    }
    return render(request, "seapac/agricultores/flow_agricultor.html", context)


@never_cache
@login_required
@group_required('AGRICULTORES')
def renda_agricultor(request, id, ano):
    family = get_object_or_404(Family, id=id)
    renda = get_object_or_404(FamilyRenda, family=family, ano=ano)
    resultado = renda.calcular_renda()

    renda_total = resultado["renda_total"]
    renda_potencial = resultado["renda_total_potencial"]
    
    renda_total = renda_total.replace('.', '').replace(',','.')
    renda_potencial = renda_potencial.replace('.', '').replace(',','.')

    color_result = "var(--secondary-green)"

    if float(renda_total) < 0:
        color_result="var(--error)"

    color_result_potencial = "var(--secondary-green)"
    if float(renda_potencial) < 0:
        color_result_potencial="var(--error)"


    context = {
        "family": family,
        "ano": ano,
        "total_receita": resultado["total_receita"],
        "total_custo": resultado["total_custo"],
        "renda_total": resultado["renda_total"],
        "total_receita_potencial": resultado["total_receita_potencial"],
        "renda_total_potencial": resultado["renda_total_potencial"],
        "title": f"Renda da ",
        "diferenca": resultado["diferenca"],
        "color_result": color_result,
        "color_result_potencial":color_result_potencial,

    }
    return render(request, "seapac/agricultores/renda_agricultor.html", context)


@never_cache
@login_required
@group_required('AGRICULTORES')
def renda_details_agricultor(request, id, ano):
    family = get_object_or_404(Family, id=id)
    renda = get_object_or_404(FamilyRenda, family=family, ano=ano)
    resultado = renda.calcular_renda()

    context = {
        "family": family,
        "ano": ano,
        "produtos": resultado["produtos"],
        "title": f"Detalhamento da renda da",
    }
    return render(request, "seapac/agricultores/renda_details_agricultor.html", context)

@never_cache
@login_required
@group_required('AGRICULTORES')
def subsystems_agricultor(request):
    family = get_object_or_404(Family, agricultor=request.user)
    rendas = FamilyRenda.objects.filter(family=family).order_by("-ano")

    rendas_lista = list(rendas)
    print(f"rendas_lista: \n{rendas_lista}")
    ano_recente = rendas_lista[0].ano
    print(f"\nano mais recente selecionado: \n{ano_recente}")


    family_subsystems = FamilySubsystem.objects.filter(
            family_renda=FamilyRenda.objects.filter(family=family, ano=ano_recente)[:1]
        ).select_related(
        "subsystem"
    )

    print(f'\nfamily_subsystems:\n{family_subsystems}')

    subsystems_data = []
    for family_subsystem in family_subsystems:
        subsystems_data.append({
            "id": family_subsystem.subsystem.id,
            "nome_subsistema": family_subsystem.subsystem.nome_subsistema,
            "tipo": family_subsystem.subsystem.tipo,
        })

    print(f"\nsubsystems_data: \n{subsystems_data}")
    
    context = {
        'family':family,
        'subsystems':subsystems_data,
        'ano':ano_recente,
        'title': "Meus subsistemas",
    }
    return render(request, "seapac/agricultores/subsistemas_agricultor.html", context)


@never_cache
@login_required
@group_required('AGRICULTORES')
def timeline_agricultor(request, agricultor_id):
    user_agricultor = get_object_or_404(Agricultor, id=agricultor_id)
    family_agricultor = get_object_or_404(Family, agricultor=user_agricultor)

    return redirect('timeline', id=family_agricultor.id)
