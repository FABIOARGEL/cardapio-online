// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Main Application Init
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide icons
    if (window.lucide) {
        window.lucide.createIcons();
    }
    
    // Auth object should be globally available
    if (window.Auth) {
        window.Auth.enforcePermissions();
        window.Auth.updateUI();
    }
    
    // Cart object should be globally available
    if (window.Cart) {
        window.Cart.updateBadge();
    }
});
