from django.middleware.csrf import CsrfViewMiddleware
from django.conf import settings


class ReplitCsrfMiddleware(CsrfViewMiddleware):
    """
    Middleware customizado para contornar problemas de CSRF no ambiente Replit
    """
    
    def process_view(self, request, callback, callback_args, callback_kwargs):
        """
        Contorna verificação CSRF em ambiente de desenvolvimento Replit
        """
        # Em ambiente de desenvolvimento e domínio Replit, pule a verificação CSRF
        if settings.DEBUG and hasattr(request, 'META'):
            host = request.META.get('HTTP_HOST', '')
            if '.replit.dev' in host or 'localhost' in host:
                # Marca a view como isenta de CSRF
                setattr(callback, 'csrf_exempt', True)
        
        # Chama o método pai
        return super().process_view(request, callback, callback_args, callback_kwargs)