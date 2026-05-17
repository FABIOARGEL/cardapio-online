// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CEP Helper
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const CEPHelper = {
    mask(value) {
        return value
            .replace(/\D/g, '')
            .replace(/(\d{5})(\d)/, '$1-$2')
            .replace(/(-\d{3})\d+?$/, '$1');
    },
    async fetch(cep) {
        const cleanCep = cep.replace(/\D/g, '');
        if (cleanCep.length !== 8) return null;
        try {
            const res = await window.fetch(`https://viacep.com.br/ws/${cleanCep}/json/`);
            if (!res.ok) return null;
            const data = await res.json();
            if (data.erro) return null;
            return data;
        } catch (e) {
            return null;
        }
    },
    init(cepInputId, fieldMap) {
        const cepInput = document.getElementById(cepInputId);
        if (!cepInput) return;
        
        cepInput.addEventListener('input', async (e) => {
            let val = e.target.value;
            val = this.mask(val);
            e.target.value = val;
            
            if (val.replace(/\D/g, '').length === 8) {
                const data = await this.fetch(val);
                if (data) {
                    if (fieldMap.street) {
                        const el = document.getElementById(fieldMap.street);
                        if (el) el.value = data.logradouro || el.value;
                    }
                    if (fieldMap.neighborhood) {
                        const el = document.getElementById(fieldMap.neighborhood);
                        if (el) el.value = data.bairro || el.value;
                    }
                    if (fieldMap.city) {
                        const el = document.getElementById(fieldMap.city);
                        if (el) el.value = data.localidade || el.value;
                    }
                    if (fieldMap.state) {
                        const el = document.getElementById(fieldMap.state);
                        if (el) el.value = data.uf || el.value;
                    }
                    if (fieldMap.complement && data.complemento) {
                        const el = document.getElementById(fieldMap.complement);
                        if (el && !el.value) el.value = data.complemento;
                    }
                    
                    if (fieldMap.number) {
                        const numEl = document.getElementById(fieldMap.number);
                        if (numEl) numEl.focus();
                    }
                }
            }
        });
    }
};

// Attach to window for inline scripts compatibility
window.CEPHelper = CEPHelper;
