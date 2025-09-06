from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timedelta
import json
import logging

from .models import Comerciante, Funcionario, Servico, Cliente, Agendamento

logger = logging.getLogger(__name__)


def agendar_servico(request, comerciante_id):
    """Página pública de agendamento para clientes"""
    comerciante = get_object_or_404(Comerciante, id=comerciante_id, ativo=True)
    
    context = {
        'comerciante': comerciante,
        'servicos': comerciante.servicos.filter(ativo=True),
        'funcionarios': comerciante.funcionarios.filter(ativo=True),
    }
    
    return render(request, 'agendamento/agendamento_publico.html', context)

@csrf_exempt
def criar_agendamento(request, comerciante_id):
    """API para criar agendamento"""
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método não permitido'}, status=405)
    
    try:
        comerciante = get_object_or_404(Comerciante, id=comerciante_id, ativo=True)
        data = json.loads(request.body)
        
        # Validar dados obrigatórios
        campos_obrigatorios = ['cliente_nome', 'cliente_telefone', 'servico_id', 'funcionario_id', 'data', 'horario']
        for campo in campos_obrigatorios:
            if not data.get(campo):
                return JsonResponse({'error': f'Campo {campo} é obrigatório'}, status=400)
        
        # Buscar ou criar cliente
        email = data.get('cliente_email', '').strip()
        telefone = data.get('cliente_telefone', '').strip()
        nome = data.get('cliente_nome', '').strip()
        
        if not nome or not telefone:
            return JsonResponse({'error': 'Nome e telefone são obrigatórios'}, status=400)
        
        # Tentar buscar cliente primeiro pelo email se fornecido, senão pelo telefone
        cliente = None
        if email:
            try:
                cliente = Cliente.objects.get(email=email, comerciante=comerciante)
            except Cliente.DoesNotExist:
                pass
        
        if not cliente and telefone:
            try:
                cliente = Cliente.objects.get(telefone=telefone, comerciante=comerciante)
            except Cliente.DoesNotExist:
                pass
        
        # Se cliente não existe, criar novo
        if not cliente:
            cliente = Cliente.objects.create(
                nome=nome,
                email=email,
                telefone=telefone,
                comerciante=comerciante
            )
        else:
            # Atualizar dados se necessário
            cliente.nome = nome
            if email:
                cliente.email = email
            cliente.save()
        
        # Buscar serviço e funcionário
        try:
            servico = get_object_or_404(Servico, id=data['servico_id'], comerciante=comerciante, ativo=True)
            funcionario = get_object_or_404(Funcionario, id=data['funcionario_id'], comerciante=comerciante, ativo=True)
        except:
            return JsonResponse({'error': 'Serviço ou funcionário não encontrado'}, status=400)
        
        # Criar data e hora do agendamento
        try:
            data_str = data['data']
            horario_str = data['horario']
            data_agendamento = datetime.strptime(f"{data_str} {horario_str}", '%Y-%m-%d %H:%M')
            
            # Garantir que o datetime está no timezone correto
            if timezone.is_naive(data_agendamento):
                data_agendamento = timezone.make_aware(data_agendamento)
        except ValueError:
            return JsonResponse({'error': 'Data ou horário inválido'}, status=400)
        
        # Verificar se a data não é no passado
        if data_agendamento < timezone.now():
            return JsonResponse({'error': 'Não é possível agendar para uma data no passado'}, status=400)
        
        # Calcular horário de fim baseado na duração do serviço
        from datetime import timedelta
        data_fim = data_agendamento + timedelta(minutes=servico.duracao_minutos)
        
        # Verificar conflitos de horário
        data_inicio_novo = data_agendamento
        data_fim_novo = data_agendamento + timedelta(minutes=servico.duracao_minutos)
        
        # Buscar agendamentos do funcionário no mesmo dia
        agendamentos_existentes = Agendamento.objects.filter(
            funcionario=funcionario,
            status__in=['agendado', 'confirmado', 'em_andamento'],
            data_agendamento__date=data_agendamento.date()
        )
        
        # Verificar se há sobreposição de horários
        tem_conflito = False
        for agendamento_existente in agendamentos_existentes:
            data_inicio_existente = agendamento_existente.data_agendamento
            data_fim_existente = agendamento_existente.get_data_fim()
            
            # Verificar se há sobreposição
            if (data_inicio_novo < data_fim_existente and data_fim_novo > data_inicio_existente):
                tem_conflito = True
                break
        
        if tem_conflito:
            return JsonResponse({'error': 'Horário não está mais disponível'}, status=400)
        
        # Gerar token de confirmação
        import uuid
        token_confirmacao = str(uuid.uuid4())
        
        # Criar agendamento
        agendamento = Agendamento.objects.create(
            comerciante=comerciante,
            cliente=cliente,
            funcionario=funcionario,
            servico=servico,
            data_agendamento=data_agendamento,
            observacoes=data.get('observacoes', ''),
            status='agendado',
            token_confirmacao=token_confirmacao
        )
        
        # Enviar notificações
        from .tasks import enviar_confirmacao_agendamento
        enviar_confirmacao_agendamento.delay(agendamento.id)
        
        return JsonResponse({
            'success': True,
            'agendamento_id': agendamento.id,
            'message': 'Agendamento criado com sucesso!',
            'redirect_url': f'/agendamento/confirmado/{agendamento.id}/',
            'detalhes': {
                'data': agendamento.data_agendamento.strftime('%d/%m/%Y'),
                'horario': agendamento.data_agendamento.strftime('%H:%M'),
                'servico': agendamento.servico.nome,
                'funcionario': agendamento.funcionario.user.get_full_name(),
                'valor': str(agendamento.servico.preco),
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Dados JSON inválidos'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Erro ao criar agendamento: {str(e)}')
        return JsonResponse({'error': 'Erro interno do servidor'}, status=500)

def get_funcionarios_servico(request, comerciante_id, servico_id):
    """API para obter funcionários que realizam um serviço"""
    comerciante = get_object_or_404(Comerciante, id=comerciante_id, ativo=True)
    servico = get_object_or_404(Servico, id=servico_id, comerciante=comerciante)
    
    funcionarios = servico.funcionarios.filter(ativo=True).values("id", "user__first_name", "user__last_name", "especialidades")
    funcionarios_list = [
        {
            'id': f['id'],
            'nome': f"{f['user__first_name']} {f['user__last_name']}",
            'especialidades': f['especialidades']
        }
        for f in funcionarios
    ]
    
    return JsonResponse({'funcionarios': funcionarios_list})

def get_horarios_disponiveis(request, comerciante_id, funcionario_id):
    """API para obter horários disponíveis de um funcionário"""
    comerciante = get_object_or_404(Comerciante, id=comerciante_id, ativo=True)
    funcionario = get_object_or_404(Funcionario, id=funcionario_id, comerciante=comerciante, ativo=True)
    
    data = request.GET.get('data')
    if not data:
        return JsonResponse({'erro': 'Data é obrigatória'}, status=400)
    
    try:
        # Validar formato da data
        data_obj = datetime.strptime(data, '%Y-%m-%d').date()
        
        # Não permitir agendamento para datas passadas
        if data_obj < timezone.now().date():
            return JsonResponse({'horarios': []})
        
    except ValueError:
        return JsonResponse({'erro': 'Data inválida'}, status=400)
    
    # Horários básicos (você pode personalizar conforme necessário)
    horarios_base = [
        '08:00', '08:30', '09:00', '09:30', '10:00', '10:30',
        '11:00', '11:30', '14:00', '14:30', '15:00', '15:30',
        '16:00', '16:30', '17:00', '17:30'
    ]
    
    # Se for hoje, filtrar horários que já passaram
    if data_obj == timezone.now().date():
        hora_atual = timezone.now().time()
        horarios_base = [h for h in horarios_base if datetime.strptime(h, '%H:%M').time() > hora_atual]
    
    # Buscar agendamentos existentes para essa data
    agendamentos_existentes = Agendamento.objects.filter(
        funcionario=funcionario,
        data_agendamento__date=data,
        status__in=['agendado', 'confirmado', 'em_andamento']
    )
    
    horarios_disponiveis = []
    
    for horario in horarios_base:
        try:
            horario_obj = datetime.strptime(f"{data} {horario}", '%Y-%m-%d %H:%M')
            horario_obj = timezone.make_aware(horario_obj)
            
            # Verificar se há conflito com algum agendamento existente
            # Assumindo duração padrão de 60 minutos para verificação
            duracao_padrao = 60  # minutos
            inicio_novo = horario_obj
            fim_novo = horario_obj + timedelta(minutes=duracao_padrao)
            
            tem_conflito = False
            for agendamento in agendamentos_existentes:
                inicio_existente = agendamento.data_agendamento
                fim_existente = agendamento.get_data_fim()
                
                # Verificar se há sobreposição de horários
                if (inicio_novo < fim_existente and fim_novo > inicio_existente):
                    tem_conflito = True
                    break
            
            if not tem_conflito:
                horarios_disponiveis.append(horario)
        except Exception as e:
            logger.error(f"Erro ao processar horário {horario}: {str(e)}")
            continue
    
    return JsonResponse({'horarios': horarios_disponiveis})


def get_funcionarios_por_servico(request, comerciante_id, servico_id):
    """API para obter funcionários que prestam um serviço específico"""
    comerciante = get_object_or_404(Comerciante, id=comerciante_id, ativo=True)
    servico = get_object_or_404(Servico, id=servico_id, comerciante=comerciante, ativo=True)
    
    # Por simplicidade, todos os funcionários podem prestar todos os serviços
    funcionarios = comerciante.funcionarios.filter(ativo=True)
    
    funcionarios_data = []
    for funcionario in funcionarios:
        funcionarios_data.append({
            'id': funcionario.id,
            'nome': funcionario.user.get_full_name(),
            'especialidades': funcionario.especialidades,
        })
    
    return JsonResponse({'funcionarios': funcionarios_data})








def confirmar_agendamento(request):
    """Página de confirmação do agendamento"""
    agendamento_id = request.GET.get('id')
    if not agendamento_id:
        return render(request, 'agendamento/erro.html', {'erro': 'ID do agendamento não informado'})
    
    try:
        agendamento = get_object_or_404(Agendamento, id=agendamento_id)
        context = {
            'agendamento': agendamento,
        }
        return render(request, 'agendamento/confirmacao.html', context)
    except:
        return render(request, 'agendamento/erro.html', {'erro': 'Agendamento não encontrado'})


def agendamento_sucesso(request):
    """Página de sucesso do agendamento"""
    return render(request, 'agendamento/sucesso.html')


def verificar_disponibilidade(request):
    """API para verificar disponibilidade de horários"""
    return JsonResponse({"disponivel": True})


def confirmar_agendamento_token(request, token):
    """Confirmar agendamento via token"""
    try:
        agendamento = get_object_or_404(Agendamento, token_confirmacao=token)
        
        if request.method == 'POST':
            agendamento.status = 'confirmado'
            agendamento.confirmado_pelo_cliente = True
            agendamento.save()
            
            # Notificar comerciante em tempo real
            from .consumers import send_notification_to_user
            send_notification_to_user(
                agendamento.comerciante.user.id,
                {
                    'type': 'agendamento_confirmado',
                    'message': f'Agendamento confirmado por {agendamento.cliente.nome}',
                    'agendamento_id': agendamento.id
                }
            )
            
            messages.success(request, 'Agendamento confirmado com sucesso!')
            return redirect('agendamento_confirmado', agendamento_id=agendamento.id)
        
        context = {
            'agendamento': agendamento,
            'token': token,
            'acao': 'confirmar'
        }
        return render(request, 'agendamento/confirmar_cancelar.html', context)
        
    except Agendamento.DoesNotExist:
        messages.error(request, 'Link de confirmação inválido ou expirado.')
        return render(request, 'agendamento/erro.html', {'erro': 'Link inválido'})


def cancelar_agendamento_token(request, token):
    """Cancelar agendamento via token"""
    try:
        agendamento = get_object_or_404(Agendamento, token_confirmacao=token)
        
        if request.method == 'POST':
            motivo = request.POST.get('motivo', '')
            agendamento.status = 'cancelado'
            agendamento.observacoes += f"\nCancelado pelo cliente. Motivo: {motivo}"
            agendamento.save()
            
            # Notificar comerciante em tempo real
            from .consumers import send_notification_to_user
            send_notification_to_user(
                agendamento.comerciante.user.id,
                {
                    'type': 'agendamento_cancelado',
                    'message': f'Agendamento cancelado por {agendamento.cliente.nome}',
                    'agendamento_id': agendamento.id
                }
            )
            
            messages.success(request, 'Agendamento cancelado com sucesso!')
            return redirect('agendamento_cancelado', agendamento_id=agendamento.id)
        
        context = {
            'agendamento': agendamento,
            'token': token,
            'acao': 'cancelar'
        }
        return render(request, 'agendamento/confirmar_cancelar.html', context)
        
    except Agendamento.DoesNotExist:
        messages.error(request, 'Link de cancelamento inválido ou expirado.')
        return render(request, 'agendamento/erro.html', {'erro': 'Link inválido'})


def agendamento_confirmado(request, agendamento_id):
    """Página de agendamento confirmado"""
    agendamento = get_object_or_404(Agendamento, id=agendamento_id)
    return render(request, 'agendamento/agendamento_confirmado.html', {'agendamento': agendamento})


def agendamento_cancelado(request, agendamento_id):
    """Página de agendamento cancelado"""
    agendamento = get_object_or_404(Agendamento, id=agendamento_id)
    return render(request, 'agendamento/agendamento_cancelado.html', {'agendamento': agendamento})

