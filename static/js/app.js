/* ============================================================
   InvestIQ — 3-Step Application Logic
   ============================================================ */

// ── STATE ──────────────────────────────────────────────────
const state = {
    file: null,
    fileId: null,
    filepath: null,
    selectedCompany: null,
    jobId: null,
    statusInterval: null,
    reportContent: null,
    reportFilename: null
};

// ── DOM REFERENCES ─────────────────────────────────────────
const $ = id => document.getElementById(id);
const panels = {
    upload:    $('panel-upload'),
    companies: $('panel-companies'),
    configure: $('panel-configure'),
    progress:  $('panel-progress'),
    analytics: $('panel-analytics'),
    report:    $('panel-report')
};

// ── PANEL HELPERS ──────────────────────────────────────────
function showPanel(name) {
    Object.entries(panels).forEach(([k, el]) => {
        if (el) el.style.display = k === name ? 'block' : 'none';
    });
}

function showPanels(...names) {
    Object.entries(panels).forEach(([k, el]) => {
        if (el) el.style.display = names.includes(k) ? 'block' : 'none';
    });
}

// ── STEP TRACKER ───────────────────────────────────────────
function setStep(n) {
    for (let i = 1; i <= 3; i++) {
        const node = $('sn-' + i);
        const wrap = $('sw-' + i);
        if (!node) continue;
        node.classList.remove('active', 'done');
        wrap.classList.remove('active', 'done');
        if (i < n)       { node.classList.add('done');   wrap.classList.add('done'); }
        else if (i === n) { node.classList.add('active'); wrap.classList.add('active'); }
    }
    const l12 = $('sl-12');
    const l23 = $('sl-23');
    if (l12) l12.classList.toggle('done', n > 1);
    if (l23) l23.classList.toggle('done', n > 2);
}

// ── FILE HANDLING ───────────────────────────────────────────
const dropZone  = document.querySelector('.drop-zone');
const pdfInput  = $('pdf-input');
const searchBtn = $('search-btn');

if (dropZone) {
    // Note: <label for="pdf-input"> wraps the drop zone, so native HTML
    // already opens the file dialog on click. No JS click handler needed.

    dropZone.addEventListener('dragover', e => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const f = e.dataTransfer.files[0];
        if (f) handleFileSelected(f);
    });
}

if (pdfInput) {
    pdfInput.addEventListener('change', () => {
        if (pdfInput.files[0]) handleFileSelected(pdfInput.files[0]);
    });
}

function handleFileSelected(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showError('Please select a PDF file.');
        return;
    }
    if (file.size > 50 * 1024 * 1024) {
        showError('File size must be under 50 MB.');
        return;
    }
    state.file = file;
    const title = dropZone && dropZone.querySelector('.drop-title');
    if (title) title.textContent = file.name;
    if (dropZone) dropZone.classList.add('has-file');
    if (searchBtn) searchBtn.disabled = false;
}

// ── STEP 1 → 2 : SEARCH COMPANIES ─────────────────────────
if (searchBtn) {
    searchBtn.addEventListener('click', searchCompanies);
}

async function searchCompanies() {
    if (!state.file) { showError('Please select a PDF file first.'); return; }

    searchBtn.disabled = true;
    searchBtn.textContent = 'Scanning PDF…';

    try {
        const fd = new FormData();
        fd.append('file', state.file);

        const res  = await fetch('/api/extract-companies', { method: 'POST', body: fd });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Extraction failed');

        state.fileId   = data.file_id;
        state.filepath = data.filepath;

        // Pre-fill deal params if found in PDF
        if (data.deal_info) {
            const di = data.deal_info;
            if (di.cheque_cr    && $('cheque_cr'))    $('cheque_cr').value    = di.cheque_cr;
            if (di.ownership_pct && $('ownership_pct')) $('ownership_pct').value = di.ownership_pct;
            if (di.deal_type    && $('deal_type')) {
                const sel = $('deal_type');
                for (let opt of sel.options) {
                    if (opt.value.toLowerCase() === di.deal_type.toLowerCase()) { sel.value = opt.value; break; }
                }
            }
        }

        showCompanies(data.companies || []);

    } catch (err) {
        showError(err.message || 'Failed to scan PDF.');
    } finally {
        searchBtn.disabled = false;
        searchBtn.textContent = 'Search Companies';
    }
}

// ── SHOW COMPANY CARDS ─────────────────────────────────────
const CARD_COLORS = [
    ['#1D4ED8','#3B82F6'], ['#7C3AED','#A78BFA'],
    ['#059669','#34D399'], ['#D97706','#FCD34D'],
    ['#DC2626','#F87171']
];

function colorForIndex(i) { return CARD_COLORS[i % CARD_COLORS.length]; }

function showCompanies(companies) {
    const grid = $('companies-grid');
    if (!grid) return;
    grid.innerHTML = '';

    if (companies.length === 0) {
        grid.innerHTML = '<p style="color:var(--text-2);padding:1rem 0;">No companies found. You can still proceed — select the company manually in the next step.</p>';
    }

    companies.forEach((c, i) => {
        const [c1, c2] = colorForIndex(i);
        const card = document.createElement('div');
        card.className = 'company-card' + (c.is_primary ? ' selected' : '');
        card.innerHTML = `
            <div class="cc-top">
                <div class="cc-initial" style="background:linear-gradient(135deg,${c1},${c2})">${esc(c.name[0] || '?')}</div>
                <div class="cc-meta">
                    <div class="cc-name">${esc(c.name)}</div>
                    ${c.sector ? `<span class="cc-sector">${esc(c.sector)}</span>` : ''}
                </div>
            </div>
            ${c.description ? `<div class="cc-desc">${esc(c.description)}</div>` : ''}
            <div class="cc-check">✓</div>`;

        card.addEventListener('click', () => selectCompany(card, c));
        grid.appendChild(card);

        if (c.is_primary) {
            state.selectedCompany = c;
        }
    });

    // If a primary company was pre-selected, also update the configure banner
    if (state.selectedCompany) {
        updateSelectedBanner(state.selectedCompany);
    }

    setStep(2);
    showPanel('companies');
}

function selectCompany(card, company) {
    document.querySelectorAll('.company-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    state.selectedCompany = company;
    setTimeout(() => showConfigure(company), 250);
}

// ── STEP 2 → 3 : CONFIGURE ────────────────────────────────
function showConfigure(company) {
    updateSelectedBanner(company);
    setStep(3);
    showPanel('configure');
}

function updateSelectedBanner(company) {
    const banner = $('selected-banner');
    if (!banner) return;
    const [c1, c2] = colorForIndex(0);
    banner.innerHTML = `
        <div class="sb-icon" style="width:46px;height:46px;border-radius:10px;background:linear-gradient(135deg,${c1},${c2});display:flex;align-items:center;justify-content:center;font-size:1.375rem;font-weight:700;color:white;">
            ${esc(company.name[0] || '?')}
        </div>
        <div>
            <div class="sb-label">Selected Company</div>
            <div class="sb-name">${esc(company.name)}</div>
            ${company.sector ? `<div class="sb-sector">${esc(company.sector)}</div>` : ''}
        </div>`;
}

// ── BACK BUTTONS ───────────────────────────────────────────
const btnBackUpload    = $('btn-back-upload');
const btnBackCompanies = $('btn-back-companies');

if (btnBackUpload)    btnBackUpload.addEventListener('click',    () => { setStep(1); showPanel('upload'); });
if (btnBackCompanies) btnBackCompanies.addEventListener('click', () => { setStep(2); showPanel('companies'); });

// ── ADVANCED TOGGLE ────────────────────────────────────────
const advToggle = $('adv-toggle');
const advBox    = $('adv-box');

if (advToggle && advBox) {
    advToggle.addEventListener('click', () => {
        const isOpen = advBox.style.display === 'block';
        advBox.style.display = isOpen ? 'none' : 'block';
        advToggle.classList.toggle('open', !isOpen);
        const arrow = advToggle.querySelector('.adv-arrow');
        if (arrow) arrow.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(180deg)';
    });
}

// ── STEP 3 → RUN ANALYSIS ─────────────────────────────────
const analyzeForm = $('analyze-form');
if (analyzeForm) {
    analyzeForm.addEventListener('submit', async e => {
        e.preventDefault();
        await runAnalysis();
    });
}

async function runAnalysis() {
    const btn = $('analyze-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Starting…'; }

    console.log('runAnalysis state:', { fileId: state.fileId, filepath: state.filepath, hasFile: !!state.file });

    try {
        const fd = new FormData();

        if (state.fileId) {
            fd.append('file_id', state.fileId);
            console.log('Sending file_id reference:', state.fileId);
        } else if (state.file) {
            fd.append('file', state.file);
            console.log('Sending raw file');
        } else {
            throw new Error('No file available. Please go back and re-upload the PDF.');
        }

        if (state.selectedCompany) fd.append('company_name', state.selectedCompany.name);

        // Deal params
        const fields = ['cheque_cr','ownership_pct','deal_type','multiple_low','multiple_base','multiple_high'];
        fields.forEach(f => { const el = $(f); if (el && el.value) fd.append(f, el.value); });

        const res  = await fetch('/api/upload', { method: 'POST', body: fd });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to start analysis');

        state.jobId = data.job_id;
        showPanel('progress');
        startPolling(state.jobId);

    } catch (err) {
        showError(err.message);
        if (btn) { btn.disabled = false; btn.textContent = 'Run Analysis'; }
    }
}

// ── POLLING ────────────────────────────────────────────────
const ANALYSIS_STEPS = [
    { id: 'as-1', label: 'Extracting business context…' },
    { id: 'as-2', label: 'Computing financials & valuation…' },
    { id: 'as-3', label: 'Analysing market comparables…' },
    { id: 'as-4', label: 'Generating IC report…' }
];

function startPolling(jobId) {
    if (state.statusInterval) clearInterval(state.statusInterval);
    let step = 0;
    setAnalysisStep(0);
    setProgress(5, 'Initialising…');

    state.statusInterval = setInterval(async () => {
        try {
            const res  = await fetch(`/api/status/${jobId}`);
            const data = await res.json();

            if (data.status === 'processing' || data.status === 'queued') {
                step = Math.min(step + 1, ANALYSIS_STEPS.length - 1);
                setAnalysisStep(step);
                setProgress(10 + step * 22, data.progress || ANALYSIS_STEPS[step].label);
            } else if (data.status === 'completed') {
                clearInterval(state.statusInterval);
                setAnalysisStep(ANALYSIS_STEPS.length);  // all done
                setProgress(100, 'Complete!');
                setTimeout(() => loadReport(jobId), 800);
            } else if (data.status === 'error') {
                clearInterval(state.statusInterval);
                showError(data.error || 'Processing failed.');
                showPanel('configure');
                setStep(3);
            }
        } catch { /* network blip — keep polling */ }
    }, 2500);
}

function setAnalysisStep(activeIdx) {
    ANALYSIS_STEPS.forEach((s, i) => {
        const el = $(s.id);
        if (!el) return;
        el.classList.remove('active', 'done');
        if (i < activeIdx)       el.classList.add('done');
        else if (i === activeIdx) el.classList.add('active');
    });
}

function setProgress(pct, msg) {
    const fill = $('prog-fill');
    const status = $('prog-status');
    if (fill)   fill.style.width = pct + '%';
    if (status) status.textContent = msg || '';
}

// ── LOAD REPORT ────────────────────────────────────────────
async function loadReport(jobId) {
    try {
        const res  = await fetch(`/api/report/${jobId}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to load report');

        state.reportContent  = data.report_content;
        state.reportFilename = data.filename;

        const dlBtn = $('download-btn');
        if (dlBtn) dlBtn.onclick = () => downloadReport(data.report_content, data.filename);

        displayReport(data.report_content, data.chart_data || {});

    } catch (err) {
        showError('Failed to load report: ' + err.message);
    }
}

// ── DISPLAY REPORT ─────────────────────────────────────────
function displayReport(content, chartData) {
    if (typeof destroyCharts === 'function') destroyCharts();

    const metrics = extractSummaryMetrics(content);
    const dashHTML = createSummaryDashboard(metrics, content);
    const bodyHTML = markdownToHTML(content);

    const reportBody = $('report-content');
    if (reportBody) reportBody.innerHTML = dashHTML + '<div class="report-divider"></div>' + bodyHTML;

    showPanels('analytics', 'report');

    setTimeout(() => {
        if (typeof initializeCharts === 'function') initializeCharts(content, metrics, chartData);
    }, 200);

    const analyticsEl = panels.analytics;
    if (analyticsEl) analyticsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── NEW ANALYSIS ────────────────────────────────────────────
const newAnalysisBtn = $('new-analysis-btn');
if (newAnalysisBtn) {
    newAnalysisBtn.addEventListener('click', resetAll);
}

function resetAll() {
    if (state.statusInterval) clearInterval(state.statusInterval);
    state.file = state.fileId = state.filepath = state.selectedCompany = state.jobId = null;
    state.reportContent = state.reportFilename = null;

    if (pdfInput) pdfInput.value = '';
    const title = dropZone && dropZone.querySelector('.drop-title');
    if (title) title.textContent = 'Drag & drop PDF here';
    if (dropZone) dropZone.classList.remove('has-file');
    if (searchBtn) searchBtn.disabled = true;

    hideError();
    setStep(1);
    showPanel('upload');
}

// ── UTILITY: METRICS ───────────────────────────────────────
function extractSummaryMetrics(content) {
    const metrics = {
        recommendation: null, confidence: null, fairValue: null,
        entryMultiple: null, valuationVsDeal: null, valuationPercent: null,
        ipoPE: null, ipoPriceBand: null, upsidePotential: null,
        riskLevel: null, rewardPotential: null, factors: {}
    };
    const m = (re) => { const r = content.match(re); return r || []; };
    const g = (re, grp=1) => { const r = m(re); return r[grp] || null; };

    metrics.recommendation  = g(/INVESTMENT RECOMMENDATION[\s\S]*?(STRONG BUY|BUY|CAUTIOUS BUY|HOLD|PASS)/i);
    const conf = g(/Confidence Level:.*?(\d+)\/10/i);
    if (conf) metrics.confidence = parseInt(conf);
    metrics.fairValue       = g(/Recommended Fair Value.*?[$₹]?([\d,]+)\s*Cr/i)
                           || g(/Recommended Fair Value.*?[$₹]?([\d,]+)\s*Mn/i)
                           || g(/Recommended Fair Value.*?[$₹]?([\d,]+)/i);
    const preMoney  = g(/Implied Pre-Money Entry Multiple.*?([\d.]+)x/i);
    const postMoney = g(/Implied Post-Money Entry Multiple.*?([\d.]+)x/i);
    metrics.entryMultiple = preMoney || postMoney || g(/Implied Entry Multiple.*?([\d.]+)x/i);
    if (preMoney && postMoney && preMoney !== postMoney) {
        metrics.entryMultipleLabel = `Pre: ${preMoney}x / Post: ${postMoney}x`;
    }

    const vd = content.match(/Valuation vs Current Deal:.*?(Overvalued|Fair|Undervalued).*?([\d.]+)%/i);
    if (vd) { metrics.valuationVsDeal = vd[1]; metrics.valuationPercent = vd[2]; }

    const pe = content.match(/Expected IPO Opening P\/E Ratio:.*?([\d.]+)x.*?([\d.]+)x/i);
    if (pe) metrics.ipoPE = `${pe[1]}x – ${pe[2]}x`;

    const pb = content.match(/Expected IPO Price Band.*?[$₹]?([\d,]+).*?[$₹]?([\d,]+)/i);
    if (pb) metrics.ipoPriceBand = `₹${pb[1]} – ₹${pb[2]}`;

    const up = content.match(/Upside Potential.*?([\d.]+)%\s*to\s*([\d.]+)%/i);
    if (up) metrics.upsidePotential = `${up[1]}% – ${up[2]}%`;

    metrics.riskLevel      = g(/Risk Level:.*?(Low|Medium|High)/i);
    metrics.rewardPotential = g(/Reward Potential:.*?(High|Medium|Low)/i);

    for (const match of content.matchAll(/- \*\*([^:]+):\*\*\s*([✅⚠️❌]?\s*[^\n]+)/g)) {
        metrics.factors[match[1].trim()] = match[2].trim();
    }
    return metrics;
}

function createSummaryDashboard(metrics, fullContent) {
    const recColor    = getRecommendationColor(metrics.recommendation);
    const riskColor   = getRiskColor(metrics.riskLevel);
    const rewardColor = getRewardColor(metrics.rewardPotential);

    let quickVerdict = '';
    const vm = fullContent.match(/QUICK VERDICT[\s\S]*?([^\n]+(?:\n[^\n]+){0,2})/i);
    if (vm) quickVerdict = vm[1].trim();

    const hasFairValue = !!(metrics.fairValue || metrics.entryMultiple || metrics.valuationVsDeal);
    const hasIpoData   = !!(metrics.ipoPE || metrics.ipoPriceBand || metrics.upsidePotential);
    const hasRiskData  = !!(metrics.riskLevel || metrics.rewardPotential);

    return `<div class="summary-dashboard">
        <div class="summary-header"><h2>📊 Executive Summary Dashboard</h2></div>
        <div class="summary-grid">
            <div class="summary-card recommendation-card" style="border-left:4px solid ${recColor}">
                <div class="card-icon">🎯</div>
                <div class="card-content">
                    <div class="card-label">Investment Recommendation</div>
                    <div class="card-value" style="color:${recColor}">${metrics.recommendation || 'Data unavailable — see diligence notes'}</div>
                    ${metrics.confidence ? `<div class="card-subtext">Confidence: ${metrics.confidence}/10</div>` : ''}
                </div>
            </div>
            <div class="summary-card">
                <div class="card-icon">💰</div>
                <div class="card-content">
                    <div class="card-label">Fair Value</div>
                    ${hasFairValue ? `
                        <div class="card-value">${metrics.fairValue ? `₹${metrics.fairValue} Cr` : ''}</div>
                        ${metrics.entryMultiple ? `<div class="card-subtext">Entry Multiple: ${metrics.entryMultipleLabel || metrics.entryMultiple + 'x'}</div>` : ''}
                        ${metrics.valuationVsDeal ? `<div class="card-subtext" style="color:${metrics.valuationVsDeal==='Overvalued'?'#ef4444':metrics.valuationVsDeal==='Undervalued'?'#10b981':'#64748b'}">${metrics.valuationVsDeal}${metrics.valuationPercent ? ` by ${metrics.valuationPercent}%` : ''}</div>` : ''}
                    ` : '<div class="card-value card-value-missing">Data unavailable — see diligence notes</div>'}
                </div>
            </div>
            <div class="summary-card">
                <div class="card-icon">📈</div>
                <div class="card-content">
                    <div class="card-label">IPO Price Prediction</div>
                    ${hasIpoData ? `
                        ${metrics.ipoPE ? `<div class="card-value">${metrics.ipoPE}</div>` : ''}
                        ${metrics.ipoPriceBand ? `<div class="card-subtext">Price Band: ${metrics.ipoPriceBand}</div>` : ''}
                        ${metrics.upsidePotential ? `<div class="card-subtext" style="color:#10b981">Upside: ${metrics.upsidePotential}</div>` : ''}
                    ` : '<div class="card-value card-value-missing">Data unavailable — see diligence notes</div>'}
                </div>
            </div>
            <div class="summary-card">
                <div class="card-icon">🎲</div>
                <div class="card-content">
                    <div class="card-label">Risk–Reward</div>
                    ${hasRiskData ? `
                        <div class="risk-reward-row">
                            ${metrics.riskLevel ? `<div class="risk-reward-item"><span class="risk-reward-label">Risk</span><span class="risk-reward-value" style="color:${riskColor}">${metrics.riskLevel}</span></div>` : ''}
                            ${metrics.rewardPotential ? `<div class="risk-reward-item"><span class="risk-reward-label">Reward</span><span class="risk-reward-value" style="color:${rewardColor}">${metrics.rewardPotential}</span></div>` : ''}
                        </div>
                    ` : '<div class="card-value card-value-missing">Data unavailable — see diligence notes</div>'}
                </div>
            </div>
        </div>
        ${quickVerdict ? `<div class="quick-verdict"><h3>🎯 Quick Verdict</h3><p>${esc(quickVerdict)}</p></div>` : ''}
        ${Object.keys(metrics.factors).length > 0 ? `
        <div class="key-factors">
            <h3>✅ Key Decision Factors</h3>
            <div class="factors-grid">
                ${Object.entries(metrics.factors).map(([k,v]) => {
                    const icon  = v.includes('✅') ? '✅' : v.includes('⚠️') ? '⚠️' : v.includes('❌') ? '❌' : '•';
                    const color = v.includes('✅') ? '#10b981' : v.includes('⚠️') ? '#f59e0b' : v.includes('❌') ? '#ef4444' : '#64748b';
                    return `<div class="factor-item" style="border-left:3px solid ${color}"><span class="factor-icon">${icon}</span><div class="factor-content"><div class="factor-name">${esc(k)}</div><div class="factor-value">${esc(v.replace(/[✅⚠️❌]/g,'').trim())}</div></div></div>`;
                }).join('')}
            </div>
        </div>` : ''}
    </div>`;
}

function getRecommendationColor(r) {
    if (!r) return '#64748b';
    const u = r.toUpperCase();
    if (u.includes('STRONG BUY') || u.includes('BUY')) return '#10b981';
    if (u.includes('CAUTIOUS')) return '#f59e0b';
    if (u.includes('HOLD')) return '#64748b';
    return '#ef4444';
}
function getRiskColor(r) {
    if (!r) return '#64748b';
    return r.toUpperCase() === 'LOW' ? '#10b981' : r.toUpperCase() === 'MEDIUM' ? '#f59e0b' : '#ef4444';
}
function getRewardColor(r) {
    if (!r) return '#64748b';
    return r.toUpperCase() === 'HIGH' ? '#10b981' : r.toUpperCase() === 'MEDIUM' ? '#f59e0b' : '#ef4444';
}

function markdownToHTML(content) {
    let h = content;
    h = h.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
    h = h.replace(/^### (.*$)/gim,  '<h3>$1</h3>');
    h = h.replace(/^## (.*$)/gim,   '<h2>$1</h2>');
    h = h.replace(/^# (.*$)/gim,    '<h1>$1</h1>');
    h = h.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    h = h.replace(/\*(.*?)\*/g,     '<em>$1</em>');
    h = h.replace(/^\d+\.\s+(.*$)/gim, '<li>$1</li>');
    h = h.replace(/^[-*]\s+(.*$)/gim,  '<li>$1</li>');
    h = h.replace(/(<li>.*<\/li>\n?)+/g, m => '<ul>' + m + '</ul>');
    h = h.replace(/\n\n+/g, '</p><p>');
    h = h.replace(/\n/g, '<br>');
    h = '<p>' + h + '</p>';
    h = h.replace(/<p><h([1-4])>/g,    '<h$1>');
    h = h.replace(/<\/h([1-4])><\/p>/g, '</h$1>');
    h = h.replace(/<p><ul>/g, '<ul>');
    h = h.replace(/<\/ul><\/p>/g, '</ul>');
    h = h.replace(/<p>\s*<\/p>/g, '');
    h = h.replace(/<p><br><\/p>/g, '');
    return h;
}

function downloadReport(content, filename) {
    const blob = new Blob([content], { type: 'text/markdown' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = filename || 'PreIPO_Diligence_Report.md';
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
}

// ── ERROR TOAST ────────────────────────────────────────────
function showError(msg) {
    const toast = $('error-toast');
    const msgEl = $('error-msg');
    if (msgEl) msgEl.textContent = msg;
    if (toast) toast.style.display = 'flex';
}
function hideError() {
    const toast = $('error-toast');
    if (toast) toast.style.display = 'none';
}
const etClose = document.querySelector('.et-close');
if (etClose) etClose.addEventListener('click', hideError);

// ── HTML ESCAPE ────────────────────────────────────────────
function esc(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ── INIT ───────────────────────────────────────────────────
(function init() {
    // Hide all panels except upload on load
    showPanel('upload');
    setStep(1);
    if (searchBtn) searchBtn.disabled = true;
    if (advBox) advBox.style.display = 'none';
})();
