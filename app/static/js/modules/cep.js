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
                    if (fieldMap.rua) {
                        const el = document.getElementById(fieldMap.rua);
                        if (el) el.value = data.logradouro || el.value;
                    }
                    if (fieldMap.bairro) {
                        const el = document.getElementById(fieldMap.bairro);
                        if (el) el.value = data.bairro || el.value;
                    }
                    if (fieldMap.cidade) {
                        const el = document.getElementById(fieldMap.cidade);
                        if (el) el.value = data.localidade || el.value;
                    }
                    if (fieldMap.estado) {
                        const el = document.getElementById(fieldMap.estado);
                        if (el) el.value = data.uf || el.value;
                    }
                    if (fieldMap.complemento && data.complemento) {
                        const el = document.getElementById(fieldMap.complemento);
                        if (el && !el.value) el.value = data.complemento;
                    }
                    
                    if (fieldMap.numero) {
                        const numEl = document.getElementById(fieldMap.numero);
                        if (numEl) numEl.focus();
                    }
                }
            }
        });
    }
};

// Attach to window for inline scripts compatibility
window.CEPHelper = CEPHelper;
