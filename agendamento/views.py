from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import Comerciante, Funcionario, Servico, Cliente, Agendamento


def agendar_servico(request, comerciante_id):
    """Página pública de agendamento para clientes"""
    comerciante = get_object_or_404(Comerciante, id=comerciante_id, ativo=True)
    
    context = {
        'comerciante': comerciante,
        'servicos': comerciante.servicos.filter(ativo=True),
        'funcionarios': comerciante.funcionarios.filter(ativo=True),
    }
    
    return render(request, 'agendamento/agendamento_publico.html', context)


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


def get_horarios_disponiveis(request, comerciante_id, funcionario_id):
    """API para obter horários disponíveis de um funcionário"""
    comerciante = get_object_or_404(Comerciante, id=comerciante_id, ativo=True)
    funcionario = get_object_or_404(Funcionario, id=funcionario_id, comerciante=comerciante, ativo=True)
    
    data_str = request.GET.get('data')
    if not data_str:
        return JsonResponse({'error': 'Data não informada'}, status=400)
    
    try:
        data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Formato de data inválido'}, status=400)
    
    # Verificar se a data não é no passado
    if data_selecionada < timezone.now().date():
        return JsonResponse({'error': 'Não é possível agendar para datas passadas'}, status=400)
    
    # Gerar horários disponíveis (8h às 18h, de hora em hora)
    horarios_base = []
    for hora in range(8, 18):
        horarios_base.append(f"{hora:02d}:00")
        horarios_base.append(f"{hora:02d}:30")
    
    # Verificar agendamentos existentes
    agendamentos_existentes = Agendamento.objects.filter(
        funcionario=funcionario,
        data_agendamento__date=data_selecionada,
        status__in=['agendado', 'confirmado']
    ).values_list('data_agendamento__time', flat=True)
    
    horarios_ocupados = [agendamento.strftime('%H:%M') for agendamento in agendamentos_existentes]
    
    # Filtrar horários disponíveis
    horarios_disponiveis = []
    for horario in horarios_base:
        if horario not in horarios_ocupados:
            horarios_disponiveis.append(horario)
    
    return JsonResponse({'horarios': horarios_disponiveis})


@csrf_exempt
def criar_agendamento(request, comerciante_id):
    """API para criar um novo agendamento"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    comerciante = get_object_or_404(Comerciante, id=comerciante_id, ativo=True)
    
    # Validar dados obrigatórios
    required_fields = ['servico_id', 'funcionario_id', 'data', 'horario', 'cliente_nome', 'cliente_telefone']
    for field in required_fields:
        if not data.get(field):
            return JsonResponse({'error': f'Campo {field} é obrigatório'}, status=400)
    
    try:
        # Obter serviço e funcionário
        servico = get_object_or_404(Servico, id=data['servico_id'], comerciante=comerciante, ativo=True)
        funcionario = get_object_or_404(Funcionario, id=data['funcionario_id'], comerciante=comerciante, ativo=True)
        
        # Criar ou obter cliente
        cliente, created = Cliente.objects.get_or_create(
            telefone=data['cliente_telefone'],
            defaults={
                'nome': data['cliente_nome'],
                'email': data.get('cliente_email', ''),
            }
        )
        
        # Se cliente já existe, atualizar nome se necessário
        if not created and cliente.nome != data['cliente_nome']:
            cliente.nome = data['cliente_nome']
            if data.get('cliente_email'):
                cliente.email = data['cliente_email']
            cliente.save()
        
        # Criar data e hora do agendamento
        data_agendamento = datetime.strptime(f"{data['data']} {data['horario']}", '%Y-%m-%d %H:%M')
        data_agendamento = timezone.make_aware(data_agendamento)
        
        # Verificar se horário ainda está disponível
        agendamento_existente = Agendamento.objects.filter(
            funcionario=funcionario,
            data_agendamento=data_agendamento,
            status__in=['agendado', 'confirmado']
        ).exists()
        
        if agendamento_existente:
            return JsonResponse({'error': 'Horário não está mais disponível'}, status=400)
        
        # Criar agendamento
        agendamento = Agendamento.objects.create(
            comerciante=comerciante,
            cliente=cliente,
            servico=servico,
            funcionario=funcionario,
            data_agendamento=data_agendamento,
            observacoes=data.get('observacoes', ''),
            status='agendado'
        )
        
        return JsonResponse({
            'success': True,
            'agendamento_id': agendamento.id,
            'message': 'Agendamento criado com sucesso!',
            'detalhes': {
                'data': agendamento.data_agendamento.strftime('%d/%m/%Y'),
                'horario': agendamento.data_agendamento.strftime('%H:%M'),
                'servico': agendamento.servico.nome,
                'funcionario': agendamento.funcionario.user.get_full_name(),
                'valor': str(agendamento.servico.preco),
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=500)


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

