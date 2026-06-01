// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Auth Helper
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const Auth = {
    getToken() { return localStorage.getItem('access_token'); },
    getRefreshToken() { return localStorage.getItem('refresh_token'); },
    getUser() { const u = localStorage.getItem('user'); return u ? JSON.parse(u) : null; },
    
    setAuth(data) {
        if (data.access_token) localStorage.setItem('access_token', data.access_token);
        if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token);
        if (data.user) localStorage.setItem('user', JSON.stringify(data.user));
        this.enforcePermissions();
        this.updateUI();
    },
    
    logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login/';
    },
    
    isAuthenticated() { return !!this.getToken(); },
    isOwner() { const u = this.getUser(); return u && u.papel === 'dono'; },
    
    enforcePermissions() {
        const user = this.getUser();
        const path = window.location.pathname;
        
        // Paths specific to roles
        const isOwnerPath = path.startsWith('/dashboard');
        const isCustomerPath = ['/carrinho', '/checkout', '/perfil', '/meus-pedidos', '/pedido'].some(p => path.startsWith(p));
        const isAuthPath = ['/login', '/cadastro'].some(p => path.startsWith(p));
        const isHomePath = path === '/' || path.startsWith('/restaurantes') || path.startsWith('/restaurante/');

        if (user) {
            if (isAuthPath) {
                window.location.href = user.papel === 'dono' ? '/dashboard/' : '/';
                return;
            }
            
            if (user.papel === 'dono') {
                if (isCustomerPath || isHomePath) {
                    window.location.href = '/dashboard/';
                    return;
                }
            } else if (user.papel === 'cliente') {
                if (isOwnerPath) {
                    window.location.href = '/';
                    return;
                }
            }
        } else {
            if (isOwnerPath || isCustomerPath) {
                window.location.href = '/login/';
                return;
            }
        }
    },

    updateUI() {
        const user = this.getUser();
        const authBtns = document.getElementById('auth-buttons');
        const userMenu = document.getElementById('user-menu');
        const userName = document.getElementById('user-name');
        const dashboardLink = document.getElementById('nav-dashboard');
        const profileLink = document.getElementById('nav-profile');
        const ordersLink = document.getElementById('nav-orders');
        const cartLink = document.getElementById('nav-cart');
        const centerLinks = document.getElementById('nav-center-links');
        const ordersHeaderLink = document.getElementById('nav-orders-header');

        if (user && authBtns && userMenu) {
            authBtns.classList.add('hidden');
            userMenu.classList.remove('hidden');
            if (userName) userName.textContent = user.nome;
            
            if (user.papel === 'dono') {
                if (dashboardLink) dashboardLink.classList.remove('hidden');
                if (profileLink) profileLink.classList.add('hidden');
                if (ordersLink) ordersLink.classList.add('hidden');
                if (cartLink) cartLink.classList.add('hidden');
                if (centerLinks) centerLinks.style.display = 'none';
                if (ordersHeaderLink) ordersHeaderLink.classList.add('hidden');
            } else {
                if (dashboardLink) dashboardLink.classList.add('hidden');
                if (profileLink) profileLink.classList.remove('hidden');
                if (ordersLink) ordersLink.classList.remove('hidden');
                if (cartLink) cartLink.classList.remove('hidden');
                if (centerLinks) centerLinks.style.display = '';
                if (ordersHeaderLink) ordersHeaderLink.classList.remove('hidden');
            }
        } else if (authBtns && userMenu) {
            authBtns.classList.remove('hidden');
            userMenu.classList.add('hidden');
            if (dashboardLink) dashboardLink.classList.add('hidden');
            if (profileLink) profileLink.classList.add('hidden');
            if (ordersLink) ordersLink.classList.add('hidden');
            if (ordersHeaderLink) ordersHeaderLink.classList.add('hidden');
        }
    }
};

// Attach to window for inline scripts compatibility
window.Auth = Auth;
