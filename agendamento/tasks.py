
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Agendamento
from .notifications import NotificationService
from .consumers import send_notification_to_user
import logging

logger = logging.getLogger(__name__)

@shared_task
def enviar_confirmacao_agendamento(agendamento_id):
    """Task para enviar confirmação de agendamento"""
    try:
        agendamento = Agendamento.objects.get(id=agendamento_id)
        notification_service = NotificationService()
        notification_service.enviar_confirmacao_agendamento(agendamento)
        
        # Enviar notificação em tempo real para o comerciante
        try:
            send_notification_to_user(
                agendamento.comerciante.user.id,
                {
                    'type': 'novo_agendamento',
                    'message': f'Novo agendamento: {agendamento.cliente.nome} - {agendamento.servico.nome}',
                    'agendamento_id': agendamento.id
                }
            )
        except Exception as notification_error:
            logger.warning(f"Erro ao enviar notificação em tempo real: {str(notification_error)}")
        
    except Agendamento.DoesNotExist:
        logger.error(f"Agendamento {agendamento_id} não encontrado")
    except Exception as e:
        logger.error(f"Erro ao enviar confirmação para agendamento {agendamento_id}: {str(e)}")

@shared_task
def verificar_agendamentos_perdidos():
    """Task para verificar agendamentos que não foram comparecidos"""
    try:
        # Buscar agendamentos que já passaram e ainda estão como 'agendado' ou 'confirmado'
        agora = timezone.now()
        limite_passado = agora - timedelta(hours=1)  # 1 hora de tolerância
        
        agendamentos_perdidos = Agendamento.objects.filter(
            data_agendamento__lt=limite_passado,
            status__in=['agendado', 'confirmado']
        )
        
        for agendamento in agendamentos_perdidos:
            agendamento.status = 'nao_compareceu'
            agendamento.save()
            
            # Notificar comerciante
            send_notification_to_user(
                agendamento.comerciante.user.id,
                {
                    'type': 'cliente_nao_compareceu',
                    'message': f'Cliente não compareceu: {agendamento.cliente.nome}',
                    'agendamento_id': agendamento.id
                }
            )
        
        logger.info(f"Marcados {agendamentos_perdidos.count()} agendamentos como não compareceu")
        
    except Exception as e:
        logger.error(f"Erro ao verificar agendamentos perdidos: {str(e)}")

@shared_task
def enviar_lembretes_agendamentos():
    """Task para enviar lembretes de agendamentos"""
    try:
        # Buscar agendamentos nas próximas 24 horas
        agora = timezone.now()
        limite_lembrete = agora + timedelta(hours=24)
        
        agendamentos = Agendamento.objects.filter(
            data_agendamento__gte=agora,
            data_agendamento__lte=limite_lembrete,
            status__in=['agendado', 'confirmado'],
            lembrete_enviado=False
        )
        
        notification_service = NotificationService()
        
        for agendamento in agendamentos:
            notification_service.enviar_lembrete_agendamento(agendamento)
            
            # Marcar lembrete como enviado
            agendamento.lembrete_enviado = True
            agendamento.save()
            
            # Enviar notificação em tempo real
            send_notification_to_user(
                agendamento.funcionario.user.id,
                {
                    'type': 'lembrete_agendamento',
                    'message': f'Agendamento em breve: {agendamento.cliente.nome}',
                    'agendamento_id': agendamento.id
                }
            )
        
        logger.info(f"Lembretes enviados para {agendamentos.count()} agendamentos")
        
    except Exception as e:
        logger.error(f"Erro ao enviar lembretes: {str(e)}")
