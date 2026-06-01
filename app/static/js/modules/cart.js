// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Cart Manager
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const Cart = {
    KEY: 'cart_v2', // Changed key to avoid conflicts with old cart
    
    get() { 
        const c = localStorage.getItem(this.KEY); 
        return c ? JSON.parse(c) : { items: [] }; 
    },
    
    save(cart) { 
        localStorage.setItem(this.KEY, JSON.stringify(cart)); 
        this.updateBadge(); 
    },
    
    add(product, restaurantId, restaurantName) {
        let cart = this.get();
        const existing = cart.items.find(i => i.product_id === product.id);
        if (existing) { 
            existing.quantity = Math.min(99, existing.quantity + 1); 
        } else { 
            cart.items.push({ 
                product_id: product.id, 
                nome: product.nome, 
                preco: product.preco, 
                image_url: product.image_url || product.imagem_url, 
                quantity: 1,
                restaurante_id: restaurantId,
                restaurante_nome: restaurantName
            }); 
        }
        this.save(cart);
        showToast(`${product.nome} adicionado ao carrinho!`);
    },
    
    updateQuantity(productId, qty) {
        const cart = this.get();
        const item = cart.items.find(i => i.product_id === productId);
        if (item) { item.quantity = Math.max(1, Math.min(99, qty)); }
        this.save(cart);
    },
    
    remove(productId) {
        const cart = this.get();
        cart.items = cart.items.filter(i => i.product_id !== productId);
        this.save(cart);
    },
    
    clear() { this.save({ items: [] }); },
    
    getTotal() { 
        const cart = this.get(); 
        return cart.items.reduce((t, i) => t + i.preco * i.quantity, 0); 
    },
    
    getTotalByRestaurant(restaurantId) { 
        const cart = this.get(); 
        return cart.items.filter(i => (i.restaurante_id || i.restaurant_id) === restaurantId).reduce((t, i) => t + i.preco * i.quantity, 0); 
    },
    
    getCount() { 
        const cart = this.get(); 
        return cart.items.reduce((t, i) => t + i.quantity, 0); 
    },
    
    getRestaurants() { 
        const cart = this.get();
        const rests = {};
        cart.items.forEach(i => {
            const rId = i.restaurante_id || i.restaurant_id;
            const rNome = i.restaurante_nome || i.restaurant_nome;
            if (!rests[rId]) rests[rId] = { id: rId, nome: rNome, items: [] };
            rests[rId].items.push(i);
        });
        return Object.values(rests);
    },
    
    updateBadge() {
        const badge = document.getElementById('cart-badge');
        const count = this.getCount();
        if (badge) { badge.textContent = count; badge.classList.toggle('hidden', count === 0); }
    }
};

// Attach to window for inline scripts compatibility
window.Cart = Cart;
