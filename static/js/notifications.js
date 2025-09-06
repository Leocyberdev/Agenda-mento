
class NotificationManager {
    constructor() {
        this.socket = null;
        this.reconnectInterval = 5000;
        this.maxReconnectAttempts = 5;
        this.reconnectAttempts = 0;
        this.isConnected = false;
        this.init();
    }

    init() {
        this.connect();
        this.setupUI();
    }

    connect() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;

        try {
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = (event) => {
                console.log('WebSocket conectado');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);
            };

            this.socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleNotification(data);
            };

            this.socket.onclose = (event) => {
                console.log('WebSocket desconectado');
                this.isConnected = false;
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            };

            this.socket.onerror = (error) => {
                console.error('Erro no WebSocket:', error);
                this.updateConnectionStatus(false);
            };

        } catch (error) {
            console.error('Erro ao conectar WebSocket:', error);
            this.attemptReconnect();
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Tentativa de reconexão ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            
            setTimeout(() => {
                this.connect();
            }, this.reconnectInterval);
        } else {
            console.log('Máximo de tentativas de reconexão atingido');
            this.showReconnectButton();
        }
    }

    handleNotification(data) {
        console.log('Notificação recebida:', data);

        switch (data.type) {
            case 'connection_established':
                console.log('Conexão estabelecida:', data.message);
                break;
            
            case 'novo_agendamento':
                this.showNotification('Novo Agendamento', data.message, 'success');
                this.updateAgendamentosCount();
                this.playNotificationSound();
                break;
            
            case 'agendamento_confirmado':
                this.showNotification('Agendamento Confirmado', data.message, 'info');
                this.updateAgendamentosStatus(data.agendamento_id, 'confirmado');
                break;
            
            case 'agendamento_cancelado':
                this.showNotification('Agendamento Cancelado', data.message, 'warning');
                this.updateAgendamentosStatus(data.agendamento_id, 'cancelado');
                break;
            
            case 'lembrete_agendamento':
                this.showNotification('Lembrete', data.message, 'info');
                break;
            
            case 'cliente_nao_compareceu':
                this.showNotification('Cliente Não Compareceu', data.message, 'danger');
                this.updateAgendamentosStatus(data.agendamento_id, 'nao_compareceu');
                break;
        }
    }

    showNotification(title, message, type = 'info') {
        // Criar notificação toast
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <strong>${title}</strong><br>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;

        // Adicionar ao container de toasts
        const toastContainer = document.getElementById('toast-container');
        if (toastContainer) {
            toastContainer.insertAdjacentHTML('beforeend', toastHtml);
            const toastElement = toastContainer.lastElementChild;
            const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
            toast.show();

            // Remover toast após ser escondido
            toastElement.addEventListener('hidden.bs.toast', () => {
                toastElement.remove();
            });
        }

        // Mostrar notificação do browser se permitido
        if (Notification.permission === 'granted') {
            new Notification(title, {
                body: message,
                icon: '/static/img/favicon.ico'
            });
        }
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('ws-status');
        if (statusElement) {
            if (connected) {
                statusElement.innerHTML = '<i class="fas fa-circle text-success"></i> Online';
                statusElement.className = 'text-success';
            } else {
                statusElement.innerHTML = '<i class="fas fa-circle text-danger"></i> Offline';
                statusElement.className = 'text-danger';
            }
        }
    }

    showReconnectButton() {
        const reconnectBtn = document.getElementById('reconnect-btn');
        if (reconnectBtn) {
            reconnectBtn.style.display = 'block';
            reconnectBtn.onclick = () => {
                this.reconnectAttempts = 0;
                reconnectBtn.style.display = 'none';
                this.connect();
            };
        }
    }

    updateAgendamentosCount() {
        // Atualizar contador de agendamentos se existir
        const countElement = document.getElementById('agendamentos-count');
        if (countElement) {
            const currentCount = parseInt(countElement.textContent) || 0;
            countElement.textContent = currentCount + 1;
        }
    }

    updateAgendamentosStatus(agendamentoId, newStatus) {
        // Atualizar status na lista de agendamentos se existir
        const agendamentoRow = document.querySelector(`[data-agendamento-id="${agendamentoId}"]`);
        if (agendamentoRow) {
            const statusElement = agendamentoRow.querySelector('.status-badge');
            if (statusElement) {
                statusElement.textContent = this.getStatusText(newStatus);
                statusElement.className = `badge ${this.getStatusClass(newStatus)}`;
            }
        }
    }

    getStatusText(status) {
        const statusMap = {
            'agendado': 'Agendado',
            'confirmado': 'Confirmado',
            'em_andamento': 'Em Andamento',
            'concluido': 'Concluído',
            'cancelado': 'Cancelado',
            'nao_compareceu': 'Não Compareceu'
        };
        return statusMap[status] || status;
    }

    getStatusClass(status) {
        const classMap = {
            'agendado': 'bg-primary',
            'confirmado': 'bg-success',
            'em_andamento': 'bg-warning',
            'concluido': 'bg-info',
            'cancelado': 'bg-danger',
            'nao_compareceu': 'bg-secondary'
        };
        return classMap[status] || 'bg-secondary';
    }

    playNotificationSound() {
        // Tocar som de notificação se disponível
        const audio = document.getElementById('notification-sound');
        if (audio) {
            audio.play().catch(() => {
                // Ignorar erro se não conseguir tocar o som
            });
        }
    }

    setupUI() {
        // Solicitar permissão para notificações
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }

        // Adicionar container de toasts se não existir
        if (!document.getElementById('toast-container')) {
            const toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }

        // Adicionar som de notificação
        if (!document.getElementById('notification-sound')) {
            const audio = document.createElement('audio');
            audio.id = 'notification-sound';
            audio.preload = 'auto';
            audio.innerHTML = '<source src="/static/sounds/notification.mp3" type="audio/mpeg">';
            document.body.appendChild(audio);
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// Inicializar quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    // Verificar se o usuário está logado antes de conectar
    if (document.body.dataset.userId) {
        window.notificationManager = new NotificationManager();
    }
});

// Limpar conexão ao sair da página
window.addEventListener('beforeunload', function() {
    if (window.notificationManager) {
        window.notificationManager.disconnect();
    }
});
