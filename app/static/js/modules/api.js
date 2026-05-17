// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// API Helper (Fetch with JWT)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const API = {
    async request(url, options = {}) {
        const token = Auth.getToken();
        const headers = { ...options.headers };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        if (!(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }
        const response = await fetch(url, { ...options, headers });
        if (response.status === 401) {
            const refreshed = await this.refreshToken();
            if (refreshed) return this.request(url, options);
            Auth.logout();
        }
        return response;
    },
    
    async get(url) { return this.request(url); },
    async post(url, data) {
        const isFormData = data instanceof FormData;
        return this.request(url, { method: 'POST', body: isFormData ? data : JSON.stringify(data) });
    },
    async put(url, data) { 
        const isFormData = data instanceof FormData;
        return this.request(url, { method: 'PUT', body: isFormData ? data : JSON.stringify(data) }); 
    },
    async patch(url, data) { return this.request(url, { method: 'PATCH', body: JSON.stringify(data) }); },
    async delete(url) { return this.request(url, { method: 'DELETE' }); },
    
    async refreshToken() {
        const rt = Auth.getRefreshToken();
        if (!rt) return false;
        try {
            const res = await fetch('/api/auth/refresh/', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: rt }),
            });
            if (res.ok) {
                const data = await res.json();
                localStorage.setItem('access_token', data.access_token);
                return true;
            }
        } catch {}
        return false;
    }
};

// Attach to window for inline scripts compatibility
window.API = API;
