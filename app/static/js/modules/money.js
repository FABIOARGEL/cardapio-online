// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// Money Helper
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const MoneyHelper = {
    mask(value) {
        if (value === undefined || value === null) return '';
        let v = value.toString().replace(/\D/g, '');
        if (v === '') return '';
        v = (parseInt(v, 10) / 100).toFixed(2);
        v = v.replace('.', ',');
        v = v.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.');
        return v;
    },
    unmask(value) {
        if (!value) return 0;
        let v = value.toString().replace(/\./g, '').replace(',', '.');
        return parseFloat(v) || 0;
    },
    format(floatValue) {
        if (floatValue === undefined || floatValue === null) return '';
        const asIntStr = Math.round(parseFloat(floatValue) * 100).toString();
        return this.mask(asIntStr);
    },
    init(inputId) {
        const input = document.getElementById(inputId);
        if (!input) return;
        
        if (input.type === 'number') {
            input.type = 'text';
            if (input.value) {
                input.value = this.format(input.value);
            }
        }
        
        input.addEventListener('input', (e) => {
            e.target.value = this.mask(e.target.value);
        });
    }
};

function formatMoney(v) {
    const val = parseFloat(v) || 0;
    return `R$ ${val.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.')}`;
}

// Attach to window for inline scripts compatibility
window.MoneyHelper = MoneyHelper;
window.formatMoney = formatMoney;
