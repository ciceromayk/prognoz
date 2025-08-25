// Shared pavimentos JS: updateAreaEq, updateAreaConstr, atualizaCoef, recalcTotais

// util: parse number in Brazilian format (ex: "1.234,56" -> 1234.56)
function parseNumBR(val) {
    if (val === null || val === undefined) return 0;
    let s = String(val).trim();
    if (s === '') return 0;
    // se a string contiver vírgula, provavelmente está no formato BR
    // então removemos pontos de milhares e trocamos vírgula por ponto
    // caso contrário, preservamos o ponto (ex.: inputs type=number usam ponto como separador decimal)
    if (s.indexOf(',') !== -1) {
        s = s.replace(/\./g, '');
        s = s.replace(/,/g, '.');
    } else {
        // apenas remover espaços em branco (não tocar no ponto decimal)
        s = s.replace(/\s/g, '');
    }
    const n = parseFloat(s);
    return isNaN(n) ? 0 : n;
}

function formatBR(num) {
    return Number(num).toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2});
}

function updateAreaEq(pavId) {
    const rawArea = document.querySelector(`input[name='area_${pavId}']`)?.value || '0';
    const rawRep = document.querySelector(`input[name='rep_${pavId}']`)?.value || '0';
    const rawCoef = document.querySelector(`input[name='coef_${pavId}']`)?.value || '0';
    const area = parseNumBR(rawArea) || 0;
    const rep = parseNumBR(rawRep) || 0;
    const coef = parseNumBR(rawCoef) || 0;
    const areaEq = area * rep * coef;
    const areaEqCell = document.getElementById(`area_eq_${pavId}`);
    if (areaEqCell) areaEqCell.innerText = formatBR(areaEq);
    updateAreaConstr(pavId, area, rep);
}

function updateAreaConstr(pavId, areaValue, repValue) {
    const rawAreaVal = typeof areaValue !== 'undefined' ? areaValue : (document.querySelector(`input[name='area_${pavId}']`)?.value || '0');
    const rawRepVal = typeof repValue !== 'undefined' ? repValue : (document.querySelector(`input[name='rep_${pavId}']`)?.value || '0');
    const area = typeof areaValue !== 'undefined' ? areaValue : (parseNumBR(rawAreaVal) || 0);
    const rep = typeof repValue !== 'undefined' ? repValue : (parseNumBR(rawRepVal) || 0);
    const constrCell = document.getElementById(`area_constr_${pavId}`);
    if (!constrCell) return;
    const value = area * rep;
    constrCell.innerText = formatBR(value);
}

function atualizaCoef(select, pavId) {
    try {
        const tipo = select.value;
        const range = document.getElementById('coef_range_' + pavId);
        const num = document.querySelector(`input[name='coef_${pavId}']`);
        if (window.tiposPavimentoGlobal && window.tiposPavimentoGlobal[tipo]) {
            const [min, max] = window.tiposPavimentoGlobal[tipo];
            if (range) {
                range.min = min;
                range.max = max;
                const newv = Math.max(min, Math.min(max, parseNumBR(num?.value || min)));
                range.value = newv;
                if (min === max) {
                    range.disabled = true; range.style.opacity = 0.5; range.value = min;
                } else { range.disabled = false; range.style.opacity = 1; }
            }
            if (num) {
                const clamped = Math.max(min, Math.min(max, parseNumBR(num.value || min)));
                num.min = min; num.max = max; num.value = clamped;
            }
            const label = document.getElementById('coef_val_' + pavId);
            if (label) label.innerText = num ? num.value : '';
        }
    } catch (e) {
        console.error(e);
    }
}

function recalcTotais(forceExecution = false) {
    // Verificar se o elemento ativo é um campo de empreendimento
    const activeElement = document.activeElement;
    if (!forceExecution && activeElement && activeElement.name) {
        const empreendimentoFields = [
            'nome', 'area_terreno', 'area_privativa', 'num_unidades',
            'custo_terreno_m2', 'custo_area_privativa', 'preco_medio_venda_m2'
        ];
        if (empreendimentoFields.includes(activeElement.name)) {
            console.log('Campo de empreendimento ativo, evitando recálculo:', activeElement.name);
            return;
        }
    }
    
    console.log('recalcTotais chamada - verificando contexto');
    const rows = document.querySelectorAll('tbody tr');
    if (rows.length === 0) {
        console.log('Nenhuma linha de pavimento encontrada, abortando recálculo');
        return;
    }
    console.log('Recalculando totais para', rows.length, 'pavimentos');
    let areaConstrTotal = 0;
    let areaEqTotal = 0;
    let areaPrivTotal = 0;
    const custoAreaPriv = parseNumBR(document.getElementById('custo_area_privativa')?.value) || 0;
    rows.forEach(r => {
        const repInput = r.querySelector('input[name^="rep_"]');
        const areaInput = r.querySelector('input[name^="area_"]');
        const coefInput = r.querySelector('input[name^="coef_"]');
        const excluirCheckbox = r.querySelector('input[type=checkbox][name^="excluir_"]');
        if (!repInput || !areaInput || !coefInput) return;
        const pavId = repInput.name.split('_')[1];
    const rep = parseNumBR(repInput.value || '0') || 0;
    const area = parseNumBR(areaInput.value || '0') || 0;
    const coef = parseNumBR(coefInput.value || '0') || 0;
        const isExcl = excluirCheckbox && excluirCheckbox.checked;
        const areaTotal = area * rep;
        const areaEq = areaTotal * coef;
        if (!isExcl) areaConstrTotal += areaTotal;
        areaEqTotal += areaEq;
        const tipoSelect = r.querySelector('select[name^="tipo_"]');
        const tipo = tipoSelect ? tipoSelect.value : '';
        if (tipo === 'Área Privativa (Autônoma)') areaPrivTotal += areaTotal;
        const cellAreaEq = document.getElementById(`area_eq_${pavId}`);
        if (cellAreaEq) cellAreaEq.innerText = formatBR(areaEq);
        const cellAreaConstr = document.getElementById(`area_constr_${pavId}`);
        if (cellAreaConstr) cellAreaConstr.innerText = (!isExcl ? formatBR(areaTotal) : formatBR(0));
    });
    // atualizar cards (se existirem na página)
    const setIf = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
    setIf('card_area_construida', formatBR(areaConstrTotal));
    setIf('card_area_construida_2', formatBR(areaConstrTotal));
    setIf('card_area_equivalente', formatBR(areaEqTotal));
    setIf('card_area_privativa', formatBR(areaPrivTotal));
    const custoDireto = (areaEqTotal * custoAreaPriv) || 0;
    setIf('card_custo_direto', formatBR(custoDireto));
    const custoM2 = areaConstrTotal > 0 ? (custoDireto / areaConstrTotal) : 0;
    setIf('card_custo_m2', formatBR(custoM2));
    const numUnEl = document.getElementById('proj_num_unidades_input') || document.getElementById('projeto_num_unidades') || document.getElementById('projeto_num_unidades_hidden');
    const numUn = Math.max(1, parseInt(parseNumBR(numUnEl?.value) || 1));
    setIf('card_custo_unidade', formatBR((custoDireto / (numUn || 1)) || 0));
    const rel = areaConstrTotal > 0 ? (areaPrivTotal / areaConstrTotal) : 0;
    setIf('card_rel_ap_ac', rel.toFixed(2));
}

// Only handle input events for pavimento fields that use the pattern <prefix>_<numericId>
document.addEventListener('input', function(e){
    if (!e.target || !e.target.name) return;
    // match names like rep_12, area_5, coef_3, tipo_7 (numeric id after underscore)
    const m = String(e.target.name).match(/^(rep|area|coef|tipo)_(\d+)$/);
    if (!m) return;
    // Extra check: ensure we're inside the pavimentos table section
    if (!e.target.closest('tbody') && !e.target.closest('.table-container')) return;
    const pavId = m[2];
    console.log('Pavimento field changed:', e.target.name, 'value:', e.target.value);
    try { updateAreaEq(pavId); recalcTotais(); } catch (err) { console.error(err); }
});

document.addEventListener('change', function(e){
    if (e.target && e.target.type === 'checkbox' && e.target.name && e.target.name.startsWith('excluir_')) {
        try { recalcTotais(); } catch (err) { console.error(err); }
    }
});

document.addEventListener('DOMContentLoaded', function(){
    // expose tiposPavimento globally if present in template
    if (window.__tiposPavimentoJSON) {
        window.tiposPavimentoGlobal = window.__tiposPavimentoJSON;
    }
    // wire up sliders: when slider changes, update numeric input and recalc
    const sliders = document.querySelectorAll('input[type="range"][id^="coef_range_"]');
    sliders.forEach(function(sl){
        const id = sl.id.replace('coef_range_','');
        const num = document.querySelector(`input[name='coef_${id}']`);
        sl.addEventListener('input', function(){
            if (num) num.value = this.value;
            try { updateAreaEq(id); recalcTotais(); } catch(e){ console.error(e); }
        });
        if (num) {
            num.addEventListener('input', function(){
                // clamp to range using parseNumBR
                const v = parseNumBR(this.value) || 0;
                const min = parseNumBR(sl.min || 0);
                const max = parseNumBR(sl.max || 9999);
                const newv = Math.max(min, Math.min(max, v));
                this.value = newv;
                sl.value = newv;
                try { updateAreaEq(id); recalcTotais(); } catch(e){ console.error(e); }
            });
        }
    });
    // initialize tipo selects and attach change handlers to adjust coef limits
    document.querySelectorAll('select[name^="tipo_"]').forEach(function(sel){
        const pavId = sel.name.split('_')[1];
        try { atualizaCoef(sel, pavId); } catch(e) { console.error(e); }
        sel.addEventListener('change', function(){
            try { atualizaCoef(sel, pavId); recalcTotais(); } catch(e) { console.error(e); }
        });
    });
    // initial calculation pass - forçar execução na inicialização
    try { recalcTotais(true); } catch (e) { console.error(e); }
});
