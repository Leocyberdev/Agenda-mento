from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class UserTypeMiddleware:
    """
    Middleware para controlar acesso baseado no tipo de usuário
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # URLs que não precisam de verificação
        allowed_urls = [
            '/login/',
            '/logout/',
            '/password-reset/',
            '/django-admin/',
            '/static/',
            '/media/',
        ]
        
        # URLs que começam com agendamento são públicas
        public_urls = ['/agendamento/']
        
        # Verificar se a URL atual está nas permitidas
        current_path = request.path
        
        # Permitir URLs específicas
        if any(current_path.startswith(url) for url in allowed_urls + public_urls):
            response = self.get_response(request)
            return response
        
        # Se usuário não está logado, redirecionar para login
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        # Verificar se usuário está ativo
        if not request.user.ativo:
            messages.error(request, 'Sua conta está desativada.')
            return redirect('accounts:logout')
        
        # Controle de acesso baseado no tipo de usuário
        user_type = request.user.tipo_usuario
        
        # Administradores podem acessar apenas o painel admin
        if user_type == 'admin':
            if not current_path.startswith('/admin-panel/'):
                return redirect('admin_panel:dashboard')
        
        # Comerciantes podem acessar apenas o painel comerciante
        elif user_type == 'comerciante':
            if not current_path.startswith('/comerciante/'):
                return redirect('comerciante_panel:dashboard')
        
        # Funcionários podem acessar apenas algumas partes do painel comerciante
        elif user_type == 'funcionario':
            allowed_funcionario_urls = [
                '/comerciante/funcionario-dashboard/',
                '/comerciante/agendamentos/',
                '/profile/',
            ]
            if not any(current_path.startswith(url) for url in allowed_funcionario_urls):
                return redirect('comerciante_panel:funcionario_dashboard')
        
        response = self.get_response(request)
        return response

