
import os
from celery import Celery
from celery.schedules import crontab

# Define o módulo de configurações padrão do Django para o programa 'celery'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salao_agendamento.settings')

app = Celery('salao_agendamento')

# Usando uma string aqui significa que o worker não precisa serializar
# o objeto de configuração para processos filhos.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carrega módulos de tarefas de todos os apps Django registrados.
app.autodiscover_tasks()

# Configuração de tarefas periódicas
app.conf.beat_schedule = {
    'enviar-lembretes-agendamentos': {
        'task': 'agendamento.tasks.enviar_lembretes_agendamentos',
        'schedule': crontab(minute=0, hour=8),  # Todo dia às 8h
    },
    'verificar-agendamentos-perdidos': {
        'task': 'agendamento.tasks.verificar_agendamentos_perdidos',
        'schedule': crontab(minute=0, hour='*/2'),  # A cada 2 horas
    },
}

app.conf.timezone = 'America/Sao_Paulo'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
