from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from django.urls import reverse
from django.utils import timezone # Import timezone
from accounts.models import User
from agendamento.models import Comerciante, Funcionario, Servico, Agendamento, Cliente
from datetime import datetime, timedelta
import json
import hashlib

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
@user_passes_test(is_comerciante)
def servico_delete(request, pk):
    """Exclui um serviço"""
    comerciante = request.user.comerciante
    servico = get_object_or_404(Servico, pk=pk, comerciante=comerciante)

    if request.method == 'POST':
        try:
            servico_nome = servico.nome
            servico.delete()
            messages.success(request, f'Serviço {servico_nome} excluído com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao excluir serviço: {str(e)}')
        return redirect('comerciante_panel:servicos_list')

    return render(request, 'comerciante_panel/servico_confirm_delete.html', {
        'servico': servico,
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
    try:
        funcionario = request.user.funcionario
        comerciante = funcionario.comerciante
    except:
        messages.error(request, 'Acesso negado. Você não está cadastrado como funcionário.')
        return redirect('accounts:login')

    # Agendamentos de hoje do funcionário
    hoje = timezone.now().date()
    agendamentos_hoje = Agendamento.objects.filter(
        funcionario=funcionario,
        data_agendamento__date=hoje
    ).order_by('data_agendamento')

    # Próximos agendamentos (próximos 7 dias)
    proxima_semana = hoje + timedelta(days=7)
    proximos_agendamentos = Agendamento.objects.filter(
        funcionario=funcionario,
        data_agendamento__date__gt=hoje,
        data_agendamento__date__lte=proxima_semana
    ).order_by('data_agendamento')[:5]

    # URL do link de agendamento
    agendamento_url = request.build_absolute_uri(
        reverse('agendamento:agendar_servico', kwargs={'comerciante_id': comerciante.id})
    )

    context = {
        'funcionario': funcionario,
        'comerciante': comerciante,
        'agendamentos_hoje': agendamentos_hoje,
        'proximos_agendamentos': proximos_agendamentos,
        'agendamento_url': agendamento_url,
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

@login_required
@user_passes_test(is_comerciante)
def configuracoes(request):
    """Configurações do comerciante"""
    comerciante = request.user.comerciante

    if request.method == 'POST':
        try:
            comerciante.nome_salao = request.POST['nome_salao']
            comerciante.endereco = request.POST['endereco']
            comerciante.telefone_comercial = request.POST['telefone_comercial']
            comerciante.horario_funcionamento = request.POST['horario_funcionamento']
            comerciante.cnpj = request.POST.get('cnpj', '')

            # Upload da logo
            if 'logo' in request.FILES:
                comerciante.logo = request.FILES['logo']

            comerciante.save()

            messages.success(request, 'Configurações atualizadas com sucesso!')
            return redirect('comerciante_panel:configuracoes')

        except Exception as e:
            messages.error(request, f'Erro ao atualizar configurações: {str(e)}')

    return render(request, 'comerciante_panel/configuracoes.html', {
        'comerciante': comerciante
    })

@login_required
@user_passes_test(is_comerciante_or_funcionario)
def calendario_view(request):
    """View para exibir o calendário avançado"""
    comerciante = get_comerciante_from_user(request.user)
    
    # Buscar funcionários e suas especialidades para gerar cores
    funcionarios = comerciante.funcionarios.filter(ativo=True)
    cores_funcionarios = {}
    
    def gerar_cor_deterministica(funcionario_id):
        """Gera cor determinística e com bom contraste para funcionário"""
        # Usar hash mais robusto para cores consistentes
        hash_value = hash(str(funcionario_id))
        hue = (hash_value % 360)  # 0-359 graus no círculo de cores
        # Usar saturação alta e luminosidade média para boa visibilidade
        saturation = 70  # 70%
        lightness = 45   # 45%
        return f"hsl({hue}, {saturation}%, {lightness}%)"
    
    for funcionario in funcionarios:
        color = gerar_cor_deterministica(funcionario.id)
        cores_funcionarios[funcionario.id] = {
            'color': color,
            'nome': funcionario.user.get_full_name(),
            'especialidades': funcionario.especialidades
        }
    
    context = {
        'comerciante': comerciante,
        'funcionarios': funcionarios,
        'cores_funcionarios': json.dumps(cores_funcionarios),
        'usuario_funcionario': request.user.is_funcionario()
    }
    
    return render(request, 'comerciante_panel/calendario.html', context)

@login_required
@user_passes_test(is_comerciante_or_funcionario)
def agendamentos_json(request):
    """API para retornar agendamentos em formato JSON para o calendário"""
    comerciante = get_comerciante_from_user(request.user)
    
    # Filtros de data do FullCalendar
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    agendamentos = Agendamento.objects.filter(comerciante=comerciante).select_related(
        'cliente', 'funcionario__user', 'servico'
    )
    
    # Se for funcionário, mostrar apenas seus agendamentos
    if request.user.is_funcionario():
        agendamentos = agendamentos.filter(funcionario=request.user.funcionario)
    
    # Filtro por data se fornecido (importante para performance)
    if start:
        try:
            start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
            agendamentos = agendamentos.filter(data_agendamento__gte=start_date)
        except ValueError:
            pass  # Ignorar data inválida
    if end:
        try:
            end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
            agendamentos = agendamentos.filter(data_agendamento__lte=end_date)
        except ValueError:
            pass  # Ignorar data inválida
    
    # Converter para formato FullCalendar
    events = []
    for agendamento in agendamentos:
        # Gerar cor baseada no funcionário usando a mesma função
        hash_value = hash(str(agendamento.funcionario.id))
        hue = (hash_value % 360)
        saturation = 70
        lightness = 45
        color = f"hsl({hue}, {saturation}%, {lightness}%)"
        
        # Status do agendamento define o estilo
        class_names = ['agendamento']
        if agendamento.status == 'confirmado':
            class_names.append('confirmado')
        elif agendamento.status == 'cancelado':
            class_names.append('cancelado')
        elif agendamento.status == 'concluido':
            class_names.append('concluido')
        
        event = {
            'id': agendamento.id,
            'title': f"{agendamento.cliente.nome} - {agendamento.servico.nome}",
            'start': agendamento.data_agendamento.isoformat(),
            'end': agendamento.get_data_fim().isoformat(),
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'cliente': agendamento.cliente.nome,
                'servico': agendamento.servico.nome,
                'funcionario': agendamento.funcionario.user.get_full_name(),
                'funcionario_id': agendamento.funcionario.id,
                'preco': str(agendamento.servico.preco),
                'status': agendamento.status,
                'status_display': agendamento.get_status_display(),
                'telefone': agendamento.cliente.telefone,
                'observacoes': agendamento.observacoes or ''
            },
            'classNames': class_names
        }
        events.append(event)
    
    return JsonResponse(events, safe=False)

@login_required
@user_passes_test(is_comerciante_or_funcionario)
def mover_agendamento(request):
    """API para mover agendamento via drag & drop"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido', 'code': 'METHOD_NOT_ALLOWED'}, status=405)
    
    try:
        data = json.loads(request.body)
        agendamento_id = data.get('id')
        nova_data = data.get('start')
        
        if not agendamento_id or not nova_data:
            return JsonResponse({'error': 'Dados incompletos', 'code': 'MISSING_DATA'}, status=400)
        
        comerciante = get_comerciante_from_user(request.user)
        agendamento = get_object_or_404(Agendamento, 
                                      id=agendamento_id, 
                                      comerciante=comerciante)
        
        # Se for funcionário, só pode mover seus próprios agendamentos
        if request.user.is_funcionario() and agendamento.funcionario != request.user.funcionario:
            return JsonResponse({'error': 'Sem permissão para mover agendamentos de outros funcionários', 'code': 'PERMISSION_DENIED'}, status=403)
        
        # Converter e validar nova data
        try:
            nova_data_obj = datetime.fromisoformat(nova_data.replace('Z', '+00:00'))
            # Garantir que é timezone-aware
            if timezone.is_naive(nova_data_obj):
                nova_data_obj = timezone.make_aware(nova_data_obj)
        except ValueError:
            return JsonResponse({'error': 'Data inválida', 'code': 'INVALID_DATE'}, status=400)
        
        # Calcular nova data de fim
        nova_data_fim = nova_data_obj + timedelta(minutes=agendamento.servico.duracao_minutos)
        
        # Verificar conflitos com outros agendamentos do mesmo funcionário
        conflitos = Agendamento.objects.filter(
            funcionario=agendamento.funcionario,
            comerciante=comerciante,
            status__in=['agendado', 'confirmado', 'em_andamento']
        ).exclude(id=agendamento.id).filter(
            Q(data_agendamento__lt=nova_data_fim) & 
            Q(data_agendamento__gte=nova_data_obj) |
            Q(data_agendamento__lt=nova_data_obj) & 
            Q(data_agendamento__gt=nova_data_obj)
        )
        
        if conflitos.exists():
            conflito = conflitos.first()
            return JsonResponse({
                'error': f'Conflito de horário com agendamento de {conflito.cliente.nome} às {conflito.data_agendamento.strftime("%H:%M")}', 
                'code': 'TIME_CONFLICT'
            }, status=400)
        
        # Usar transação para garantir consistência
        with transaction.atomic():
            agendamento.data_agendamento = nova_data_obj
            agendamento.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Agendamento movido com sucesso',
            'end': nova_data_fim.isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido', 'code': 'INVALID_JSON'}, status=400)
    except Exception as e:
        # Log do erro para debugging (sem expor detalhes ao cliente)
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao mover agendamento: {str(e)}")
        return JsonResponse({'error': 'Erro interno do servidor', 'code': 'INTERNAL_ERROR'}, status=500)