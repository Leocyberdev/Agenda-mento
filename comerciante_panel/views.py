from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from django.urls import reverse
from accounts.models import User
from agendamento.models import Comerciante, Funcionario, Servico, Agendamento, Cliente
from datetime import datetime, timedelta

def is_comerciante_or_funcionario(user):
    return user.is_authenticated and (user.is_comerciante() or user.is_funcionario())

def is_comerciante(user):
    return user.is_authenticated and user.is_comerciante()

def get_comerciante_from_user(user):
    """Retorna o comerciante baseado no usuário (comerciante ou funcionário)"""
    if user.is_comerciante():
        return user.comerciante
    elif user.is_funcionario():
        return user.funcionario.comerciante
    return None

@login_required
@user_passes_test(is_comerciante_or_funcionario)
def dashboard(request):
    """Dashboard do comerciante"""
    comerciante = get_comerciante_from_user(request.user)
    
    # Estatísticas
    total_funcionarios = comerciante.funcionarios.filter(ativo=True).count()
    total_servicos = comerciante.servicos.filter(ativo=True).count()
    total_clientes = comerciante.clientes.count()
    
    # Agendamentos de hoje
    hoje = datetime.now().date()
    agendamentos_hoje = Agendamento.objects.filter(
        comerciante=comerciante,
        data_agendamento__date=hoje
    ).count()
    
    # Agendamentos recentes
    agendamentos_recentes = Agendamento.objects.filter(
        comerciante=comerciante
    ).select_related('cliente', 'funcionario', 'servico').order_by('-data_criacao')[:10]
    
    # Próximos agendamentos
    proximos_agendamentos = Agendamento.objects.filter(
        comerciante=comerciante,
        data_agendamento__gte=datetime.now(),
        status__in=['agendado', 'confirmado']
    ).select_related('cliente', 'funcionario', 'servico').order_by('data_agendamento')[:5]
    
    context = {
        'comerciante': comerciante,
        'total_funcionarios': total_funcionarios,
        'total_servicos': total_servicos,
        'total_clientes': total_clientes,
        'agendamentos_hoje': agendamentos_hoje,
        'agendamentos_recentes': agendamentos_recentes,
        'proximos_agendamentos': proximos_agendamentos,
    }
    
    return render(request, 'comerciante_panel/dashboard.html', context)

@login_required
@user_passes_test(is_comerciante)
def funcionarios_list(request):
    """Lista funcionários do comerciante"""
    comerciante = request.user.comerciante
    
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    funcionarios = Funcionario.objects.filter(comerciante=comerciante).select_related('user')
    
    if search:
        funcionarios = funcionarios.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(especialidades__icontains=search)
        )
    
    if status == 'ativo':
        funcionarios = funcionarios.filter(ativo=True)
    elif status == 'inativo':
        funcionarios = funcionarios.filter(ativo=False)
    
    funcionarios = funcionarios.order_by('-data_contratacao')
    
    # Paginação
    paginator = Paginator(funcionarios, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'comerciante': comerciante,
    }
    
    return render(request, 'comerciante_panel/funcionarios_list.html', context)

@login_required
@user_passes_test(is_comerciante)
def funcionario_create(request):
    """Cria um novo funcionário"""
    comerciante = request.user.comerciante
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Criar usuário
                user = User.objects.create_user(
                    username=request.POST['username'],
                    email=request.POST['email'],
                    password=request.POST['password'],
                    first_name=request.POST['first_name'],
                    last_name=request.POST['last_name'],
                    tipo_usuario='funcionario',
                    telefone=request.POST.get('telefone', '')
                )
                
                # Criar funcionário
                funcionario = Funcionario.objects.create(
                    user=user,
                    comerciante=comerciante,
                    especialidades=request.POST['especialidades'],
                    horario_trabalho=request.POST['horario_trabalho'],
                    comissao_percentual=request.POST.get('comissao_percentual', 30)
                )
                
                messages.success(request, f'Funcionário {funcionario.user.get_full_name()} criado com sucesso!')
                return redirect('comerciante_panel:funcionarios_list')
                
        except Exception as e:
            messages.error(request, f'Erro ao criar funcionário: {str(e)}')
    
    return render(request, 'comerciante_panel/funcionario_form.html', {
        'title': 'Criar Funcionário',
        'action': 'create',
        'comerciante': comerciante
    })

@login_required
@user_passes_test(is_comerciante)
def funcionario_edit(request, pk):
    """Edita um funcionário"""
    comerciante = request.user.comerciante
    funcionario = get_object_or_404(Funcionario, pk=pk, comerciante=comerciante)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Atualizar usuário
                user = funcionario.user
                user.username = request.POST['username']
                user.email = request.POST['email']
                user.first_name = request.POST['first_name']
                user.last_name = request.POST['last_name']
                user.telefone = request.POST.get('telefone', '')
                
                # Atualizar senha se fornecida
                if request.POST.get('password'):
                    user.set_password(request.POST['password'])
                
                user.save()
                
                # Atualizar funcionário
                funcionario.especialidades = request.POST['especialidades']
                funcionario.horario_trabalho = request.POST['horario_trabalho']
                funcionario.comissao_percentual = request.POST.get('comissao_percentual', 30)
                funcionario.ativo = request.POST.get('ativo') == 'on'
                funcionario.save()
                
                messages.success(request, f'Funcionário {funcionario.user.get_full_name()} atualizado com sucesso!')
                return redirect('comerciante_panel:funcionarios_list')
                
        except Exception as e:
            messages.error(request, f'Erro ao atualizar funcionário: {str(e)}')
    
    return render(request, 'comerciante_panel/funcionario_form.html', {
        'title': 'Editar Funcionário',
        'action': 'edit',
        'funcionario': funcionario,
        'comerciante': comerciante
    })

@login_required
@user_passes_test(is_comerciante)
def servicos_list(request):
    """Lista serviços do comerciante"""
    comerciante = request.user.comerciante
    
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    servicos = Servico.objects.filter(comerciante=comerciante).prefetch_related('funcionarios')
    
    if search:
        servicos = servicos.filter(
            Q(nome__icontains=search) |
            Q(descricao__icontains=search)
        )
    
    if status == 'ativo':
        servicos = servicos.filter(ativo=True)
    elif status == 'inativo':
        servicos = servicos.filter(ativo=False)
    
    servicos = servicos.order_by('nome')
    
    # Paginação
    paginator = Paginator(servicos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'comerciante': comerciante,
    }
    
    return render(request, 'comerciante_panel/servicos_list.html', context)

@login_required
@user_passes_test(is_comerciante)
def servico_create(request):
    """Cria um novo serviço"""
    comerciante = request.user.comerciante
    funcionarios = comerciante.funcionarios.filter(ativo=True)
    
    if request.method == 'POST':
        try:
            servico = Servico.objects.create(
                comerciante=comerciante,
                nome=request.POST['nome'],
                descricao=request.POST.get('descricao', ''),
                preco=request.POST['preco'],
                duracao_minutos=request.POST['duracao_minutos']
            )
            
            # Adicionar funcionários selecionados
            funcionarios_ids = request.POST.getlist('funcionarios')
            if funcionarios_ids:
                servico.funcionarios.set(funcionarios_ids)
            
            messages.success(request, f'Serviço {servico.nome} criado com sucesso!')
            return redirect('comerciante_panel:servicos_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao criar serviço: {str(e)}')
    
    return render(request, 'comerciante_panel/servico_form.html', {
        'title': 'Criar Serviço',
        'action': 'create',
        'funcionarios': funcionarios,
        'comerciante': comerciante
    })

@login_required
@user_passes_test(is_comerciante)
def servico_edit(request, pk):
    """Edita um serviço"""
    comerciante = request.user.comerciante
    servico = get_object_or_404(Servico, pk=pk, comerciante=comerciante)
    funcionarios = comerciante.funcionarios.filter(ativo=True)
    
    if request.method == 'POST':
        try:
            servico.nome = request.POST['nome']
            servico.descricao = request.POST.get('descricao', '')
            servico.preco = request.POST['preco']
            servico.duracao_minutos = request.POST['duracao_minutos']
            servico.ativo = request.POST.get('ativo') == 'on'
            servico.save()
            
            # Atualizar funcionários
            funcionarios_ids = request.POST.getlist('funcionarios')
            servico.funcionarios.set(funcionarios_ids)
            
            messages.success(request, f'Serviço {servico.nome} atualizado com sucesso!')
            return redirect('comerciante_panel:servicos_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao atualizar serviço: {str(e)}')
    
    return render(request, 'comerciante_panel/servico_form.html', {
        'title': 'Editar Serviço',
        'action': 'edit',
        'servico': servico,
        'funcionarios': funcionarios,
        'comerciante': comerciante
    })

@login_required
@user_passes_test(is_comerciante_or_funcionario)
def agendamentos_list(request):
    """Lista agendamentos"""
    comerciante = get_comerciante_from_user(request.user)
    
    # Filtros
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    
    agendamentos = Agendamento.objects.filter(comerciante=comerciante).select_related(
        'cliente', 'funcionario__user', 'servico'
    )
    
    # Se for funcionário, mostrar apenas seus agendamentos
    if request.user.is_funcionario():
        agendamentos = agendamentos.filter(funcionario=request.user.funcionario)
    
    if search:
        agendamentos = agendamentos.filter(
            Q(cliente__nome__icontains=search) |
            Q(cliente__email__icontains=search) |
            Q(servico__nome__icontains=search)
        )
    
    if status:
        agendamentos = agendamentos.filter(status=status)
    
    if data_inicio:
        agendamentos = agendamentos.filter(data_agendamento__date__gte=data_inicio)
    
    if data_fim:
        agendamentos = agendamentos.filter(data_agendamento__date__lte=data_fim)
    
    agendamentos = agendamentos.order_by('-data_agendamento')
    
    # Paginação
    paginator = Paginator(agendamentos, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'comerciante': comerciante,
        'status_choices': Agendamento.STATUS_CHOICES,
    }
    
    return render(request, 'comerciante_panel/agendamentos_list.html', context)

@login_required
@user_passes_test(is_comerciante_or_funcionario)
def agendamento_edit(request, pk):
    """Edita um agendamento"""
    comerciante = get_comerciante_from_user(request.user)
    agendamento = get_object_or_404(Agendamento, pk=pk, comerciante=comerciante)
    
    # Se for funcionário, só pode editar seus próprios agendamentos
    if request.user.is_funcionario() and agendamento.funcionario != request.user.funcionario:
        messages.error(request, 'Você só pode editar seus próprios agendamentos.')
        return redirect('comerciante_panel:agendamentos_list')
    
    if request.method == 'POST':
        try:
            agendamento.status = request.POST['status']
            agendamento.observacoes = request.POST.get('observacoes', '')
            
            if request.POST.get('valor_pago'):
                agendamento.valor_pago = request.POST['valor_pago']
            
            agendamento.save()
            
            messages.success(request, 'Agendamento atualizado com sucesso!')
            return redirect('comerciante_panel:agendamentos_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao atualizar agendamento: {str(e)}')
    
    return render(request, 'comerciante_panel/agendamento_form.html', {
        'agendamento': agendamento,
        'status_choices': Agendamento.STATUS_CHOICES,
        'comerciante': comerciante
    })

@login_required
@user_passes_test(is_comerciante_or_funcionario)
def funcionario_dashboard(request):
    """Dashboard específico para funcionários"""
    if not request.user.is_funcionario():
        return redirect('comerciante_panel:dashboard')
    
    funcionario = request.user.funcionario
    comerciante = funcionario.comerciante
    
    # Agendamentos do funcionário hoje
    hoje = datetime.now().date()
    agendamentos_hoje = Agendamento.objects.filter(
        funcionario=funcionario,
        data_agendamento__date=hoje
    ).select_related('cliente', 'servico').order_by('data_agendamento')
    
    # Próximos agendamentos
    proximos_agendamentos = Agendamento.objects.filter(
        funcionario=funcionario,
        data_agendamento__gte=datetime.now(),
        status__in=['agendado', 'confirmado']
    ).select_related('cliente', 'servico').order_by('data_agendamento')[:5]
    
    context = {
        'funcionario': funcionario,
        'comerciante': comerciante,
        'agendamentos_hoje': agendamentos_hoje,
        'proximos_agendamentos': proximos_agendamentos,
    }
    
    return render(request, 'comerciante_panel/funcionario_dashboard.html', context)

@login_required
@user_passes_test(is_comerciante)
def link_agendamento(request):
    """Gera link de agendamento para clientes"""
    comerciante = request.user.comerciante
    
    # URL do link de agendamento
    agendamento_url = request.build_absolute_uri(
        reverse('agendamento:agendar_servico', kwargs={'comerciante_id': comerciante.id})
    )
    
    context = {
        'comerciante': comerciante,
        'agendamento_url': agendamento_url,
    }
    
    return render(request, 'comerciante_panel/link_agendamento.html', context)
