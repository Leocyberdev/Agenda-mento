from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
import uuid
from .models import Agendamento
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        pass

    def gerar_token_confirmacao(self, agendamento):
        """Gera um token único para confirmação/cancelamento"""
        token = str(uuid.uuid4())
        agendamento.token_confirmacao = token
        agendamento.save()
        return token

    def enviar_confirmacao_agendamento(self, agendamento):
        """Envia confirmação de agendamento por email"""
        try:
            # Gerar token para confirmação/cancelamento
            token = self.gerar_token_confirmacao(agendamento)

            # Links de confirmação e cancelamento
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:5000')
            confirm_url = f"{base_url}{reverse('agendamento:confirmar_agendamento_token', args=[token])}"
            cancel_url = f"{base_url}{reverse('agendamento:cancelar_agendamento_token', args=[token])}"

            # Enviar email
            self._enviar_email_confirmacao(agendamento, confirm_url, cancel_url)

            logger.info(f"Notificação de confirmação enviada para agendamento {agendamento.id}")

        except Exception as e:
            logger.error(f"Erro ao enviar confirmação para agendamento {agendamento.id}: {str(e)}")

    def enviar_lembrete_agendamento(self, agendamento):
        """Envia lembrete do agendamento"""
        try:
            # Calcular tempo restante
            tempo_restante = agendamento.data_agendamento - timezone.now()
            horas_restantes = int(tempo_restante.total_seconds() / 3600)

            # Links de confirmação e cancelamento
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:5000')
            confirm_url = f"{base_url}{reverse('agendamento:confirmar_agendamento_token', args=[agendamento.token_confirmacao])}"
            cancel_url = f"{base_url}{reverse('agendamento:cancelar_agendamento_token', args=[agendamento.token_confirmacao])}"

            # Enviar email de lembrete
            self._enviar_email_lembrete(agendamento, horas_restantes, confirm_url, cancel_url)

            logger.info(f"Lembrete enviado para agendamento {agendamento.id}")

        except Exception as e:
            logger.error(f"Erro ao enviar lembrete para agendamento {agendamento.id}: {str(e)}")

    def _enviar_email_confirmacao(self, agendamento, confirm_url, cancel_url):
        """Envia email de confirmação de agendamento"""
        assunto = f"Agendamento Confirmado - {agendamento.comerciante.nome_salao}"

        contexto = {
            'agendamento': agendamento,
            'confirm_url': confirm_url,
            'cancel_url': cancel_url,
        }

        mensagem_html = render_to_string('notifications/email_confirmacao.html', contexto)
        mensagem_texto = render_to_string('notifications/email_confirmacao.txt', contexto)

        send_mail(
            assunto,
            mensagem_texto,
            settings.DEFAULT_FROM_EMAIL,
            [agendamento.cliente.email],
            html_message=mensagem_html,
            fail_silently=False,
        )

    def _enviar_email_lembrete(self, agendamento, horas_restantes, confirm_url, cancel_url):
        """Envia email de lembrete de agendamento"""
        assunto = f"Lembrete: Seu agendamento em {horas_restantes}h - {agendamento.comerciante.nome_salao}"

        contexto = {
            'agendamento': agendamento,
            'horas_restantes': horas_restantes,
            'confirm_url': confirm_url,
            'cancel_url': cancel_url,
        }

        mensagem_html = render_to_string('notifications/email_lembrete.html', contexto)
        mensagem_texto = render_to_string('notifications/email_lembrete.txt', contexto)

        send_mail(
            assunto,
            mensagem_texto,
            settings.DEFAULT_FROM_EMAIL,
            [agendamento.cliente.email],
            html_message=mensagem_html,
            fail_silently=False,
        )