from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Q
from django.core.paginator import Paginator
from accounts.models import User
from agendamento.models import Comerciante, Agendamento
from django.db import transaction

def is_admin(user):
    return user.is_authenticated and user.is_admin()

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """
    Dashboard principal do administrador
    """
    # Estatísticas gerais
    total_comerciantes = Comerciante.objects.filter(ativo=True).count()
    total_usuarios = User.objects.filter(ativo=True).count()
    total_agendamentos = Agendamento.objects.count()
    
    # Comerciantes recentes
    comerciantes_recentes = Comerciante.objects.filter(ativo=True).order_by('-data_criacao')[:5]
    
    # Agendamentos recentes
    agendamentos_recentes = Agendamento.objects.select_related(
        'comerciante', 'cliente', 'servico'
    ).order_by('-data_criacao')[:10]
    
    context = {
        'total_comerciantes': total_comerciantes,
        'total_usuarios': total_usuarios,
        'total_agendamentos': total_agendamentos,
        'comerciantes_recentes': comerciantes_recentes,
        'agendamentos_recentes': agendamentos_recentes,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def comerciantes_list(request):
    """
    Lista todos os comerciantes com filtros e paginação
    """
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    comerciantes = Comerciante.objects.select_related('user').annotate(
        total_agendamentos=Count('agendamentos')
    )
    
    if search:
        comerciantes = comerciantes.filter(
            Q(nome_salao__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    if status == 'ativo':
        comerciantes = comerciantes.filter(ativo=True)
    elif status == 'inativo':
        comerciantes = comerciantes.filter(ativo=False)
    
    comerciantes = comerciantes.order_by('-data_criacao')
    
    # Paginação
    paginator = Paginator(comerciantes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status': status,
    }
    
    return render(request, 'admin_panel/comerciantes_list.html', context)

@login_required
@user_passes_test(is_admin)
def comerciante_create(request):
    """
    Cria um novo comerciante
    """
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
                    tipo_usuario='comerciante',
                    telefone=request.POST.get('telefone', '')
                )
                
                # Criar comerciante
                comerciante = Comerciante.objects.create(
                    user=user,
                    nome_salao=request.POST['nome_salao'],
                    cnpj=request.POST.get('cnpj', ''),
                    endereco=request.POST['endereco'],
                    telefone_comercial=request.POST['telefone_comercial'],
                    horario_funcionamento=request.POST['horario_funcionamento']
                )
                
                messages.success(request, f'Comerciante {comerciante.nome_salao} criado com sucesso!')
                return redirect('admin_panel:comerciantes_list')
                
        except Exception as e:
            messages.error(request, f'Erro ao criar comerciante: {str(e)}')
    
    return render(request, 'admin_panel/comerciante_form.html', {
        'title': 'Criar Comerciante',
        'action': 'create'
    })

@login_required
@user_passes_test(is_admin)
def comerciante_edit(request, pk):
    """
    Edita um comerciante existente
    """
    comerciante = get_object_or_404(Comerciante, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Atualizar usuário
                user = comerciante.user
                user.username = request.POST['username']
                user.email = request.POST['email']
                user.first_name = request.POST['first_name']
                user.last_name = request.POST['last_name']
                user.telefone = request.POST.get('telefone', '')
                
                # Atualizar senha se fornecida
                if request.POST.get('password'):
                    user.set_password(request.POST['password'])
                
                user.save()
                
                # Atualizar comerciante
                comerciante.nome_salao = request.POST['nome_salao']
                comerciante.cnpj = request.POST.get('cnpj', '')
                comerciante.endereco = request.POST['endereco']
                comerciante.telefone_comercial = request.POST['telefone_comercial']
                comerciante.horario_funcionamento = request.POST['horario_funcionamento']
                comerciante.ativo = request.POST.get('ativo') == 'on'
                comerciante.save()
                
                messages.success(request, f'Comerciante {comerciante.nome_salao} atualizado com sucesso!')
                return redirect('admin_panel:comerciantes_list')
                
        except Exception as e:
            messages.error(request, f'Erro ao atualizar comerciante: {str(e)}')
    
    return render(request, 'admin_panel/comerciante_form.html', {
        'title': 'Editar Comerciante',
        'action': 'edit',
        'comerciante': comerciante
    })

@login_required
@user_passes_test(is_admin)
def comerciante_delete(request, pk):
    """
    Desativa um comerciante (soft delete)
    """
    comerciante = get_object_or_404(Comerciante, pk=pk)
    
    if request.method == 'POST':
        comerciante.ativo = False
        comerciante.user.ativo = False
        comerciante.save()
        comerciante.user.save()
        
        messages.success(request, f'Comerciante {comerciante.nome_salao} foi desativado.')
        return redirect('admin_panel:comerciantes_list')
    
    return render(request, 'admin_panel/comerciante_delete.html', {
        'comerciante': comerciante
    })
