from django.core.management.base import BaseCommand
from accounts.models import User

class Command(BaseCommand):
    help = 'Cria o usuário administrador padrão'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_user(
                username='admin',
                email='admin@salao.com',
                password='admin123',
                tipo_usuario='admin',
                first_name='Administrador',
                last_name='Sistema'
            )
            self.stdout.write(
                self.style.SUCCESS(
                    'Usuário administrador criado com sucesso!\n'
                    'Login: admin\n'
                    'Senha: admin123'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING('Usuário administrador já existe!')
            )

