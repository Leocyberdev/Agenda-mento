from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.http import HttpResponse
from .models import User
from agendamento.models import Comerciante

def login_view(request):
    """
    View para login do usuário
    """
    if request.user.is_authenticated:
        return redirect_user_dashboard(request.user)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.ativo:
                login(request, user)
                return redirect_user_dashboard(user)
            else:
                messages.error(request, 'Sua conta está desativada. Entre em contato com o administrador.')
        else:
            messages.error(request, 'Usuário ou senha inválidos.')
    
    return render(request, 'accounts/login.html')

def logout_view(request):
    """
    View para logout do usuário
    """
    logout(request)
    messages.success(request, 'Você foi desconectado com sucesso.')
    return redirect('accounts:login')

def redirect_user_dashboard(user):
    """
    Redireciona o usuário para o dashboard apropriado baseado no tipo
    """
    if user.is_admin():
        return redirect('admin_panel:dashboard')
    elif user.is_comerciante():
        return redirect('comerciante_panel:dashboard')
    elif user.is_funcionario():
        return redirect('comerciante_panel:funcionario_dashboard')
    else:
        return redirect('accounts:login')

def password_reset_request(request):
    """
    View para solicitar reset de senha
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email, ativo=True)
            
            # Gerar token de reset
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Enviar email (por enquanto apenas simular)
            current_site = get_current_site(request)
            reset_url = f"http://{current_site.domain}/reset-password/{uid}/{token}/"
            
            # Em produção, enviar email real
            print(f"Link de reset de senha para {user.email}: {reset_url}")
            
            messages.success(request, 'Um link de recuperação foi enviado para seu email.')
            return redirect('accounts:login')
            
        except User.DoesNotExist:
            messages.error(request, 'Email não encontrado.')
    
    return render(request, 'accounts/password_reset.html')

@login_required
def profile_view(request):
    """
    View para visualizar/editar perfil do usuário
    """
    return render(request, 'accounts/profile.html', {'user': request.user})

def create_admin_user():
    """
    Função para criar usuário administrador padrão
    """
    if not User.objects.filter(username='admin').exists():
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@salao.com',
            password='admin123',
            tipo_usuario='admin',
            first_name='Administrador',
            last_name='Sistema'
        )
        print("Usuário administrador criado: admin / admin123")
        return admin_user
    return None
