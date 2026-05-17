// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Toast Notifications
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function showToast(message, type = 'success') {
    const colors = { success: 'bg-emerald-500', error: 'bg-red-500', info: 'bg-blue-500', warning: 'bg-amber-500' };
    const icons = { success: 'check-circle', error: 'x-circle', info: 'info', warning: 'alert-triangle' };
    
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed top-20 right-4 z-50 space-y-2';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast flex items-center gap-3 px-5 py-3.5 rounded-2xl ${colors[type]} text-white shadow-lg`;
    toast.innerHTML = `<i data-lucide="${icons[type]}" class="w-5 h-5"></i><span class="text-sm font-medium">${message}</span>`;
    container.appendChild(toast);
    
    if (window.lucide) {
        window.lucide.createIcons();
    }
    
    setTimeout(() => toast.remove(), 3000);
}

// Attach to window for inline scripts compatibility
window.showToast = showToast;
