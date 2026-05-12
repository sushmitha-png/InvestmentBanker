// Global state
let currentJobId = null;
let statusCheckInterval = null;

// DOM Elements
const uploadForm = document.getElementById('upload-form');
const uploadSection = document.getElementById('upload-section');
const statusSection = document.getElementById('status-section');
const reportSection = document.getElementById('report-section');
const errorSection = document.getElementById('error-section');
const submitBtn = document.getElementById('submit-btn');
const fileInput = document.getElementById('pdf-file');
const fileInputLabel = document.querySelector('.file-input-label');

// File input label update
fileInput.addEventListener('change', function(e) {
    if (e.target.files.length > 0) {
        fileInputLabel.textContent = e.target.files[0].name;
    } else {
        fileInputLabel.textContent = 'Choose file...';
    }
});

// Form submission
uploadForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(uploadForm);
    const file = fileInput.files[0];
    
    if (!file) {
        showError('Please select a PDF file');
        return;
    }
    
    // Validate file type
    if (!file.type.includes('pdf') && !file.name.toLowerCase().endsWith('.pdf')) {
        showError('Please select a valid PDF file');
        return;
    }
    
    // Validate file size (50MB)
    if (file.size > 50 * 1024 * 1024) {
        showError('File size must be less than 50MB');
        return;
    }
    
    formData.append('file', file);
    
    // Disable submit button
    submitBtn.disabled = true;
    submitBtn.querySelector('.btn-text').style.display = 'none';
    submitBtn.querySelector('.btn-loader').style.display = 'inline-flex';
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Upload failed');
        }
        
        currentJobId = data.job_id;
        showStatus(data.job_id);
        startStatusChecking(data.job_id);
        
    } catch (error) {
        console.error('Upload error:', error);
        showError(error.message || 'Failed to upload file. Please try again.');
        resetSubmitButton();
    }
});

// Show status section
function showStatus(jobId) {
    hideError();
    statusSection.style.display = 'block';
    reportSection.style.display = 'none';
    updateStatus('queued', 'File uploaded, processing started...');
}

// Update status display
function updateStatus(status, progress) {
    const statusValue = document.getElementById('status-value');
    const progressValue = document.getElementById('progress-value');
    const progressFill = document.getElementById('progress-fill');
    
    statusValue.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    statusValue.className = 'status-value ' + status;
    progressValue.textContent = progress;
    
    // Update progress bar
    if (status === 'queued' || status === 'processing') {
        progressFill.style.width = '60%';
    } else if (status === 'completed') {
        progressFill.style.width = '100%';
    } else if (status === 'error') {
        progressFill.style.width = '0%';
    }
}

// Start status checking
function startStatusChecking(jobId) {
    // Clear any existing interval
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
    
    // Check status immediately
    checkStatus(jobId);
    
    // Then check every 2 seconds
    statusCheckInterval = setInterval(() => {
        checkStatus(jobId);
    }, 2000);
}

// Check job status
async function checkStatus(jobId) {
    try {
        const response = await fetch(`/api/status/${jobId}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to check status');
        }
        
        updateStatus(data.status, data.progress);
        
        if (data.status === 'completed') {
            clearInterval(statusCheckInterval);
            resetSubmitButton();
            await loadReport(jobId);
        } else if (data.status === 'error') {
            clearInterval(statusCheckInterval);
            resetSubmitButton();
            showError(data.error || 'Processing failed');
        }
        
    } catch (error) {
        console.error('Status check error:', error);
        clearInterval(statusCheckInterval);
        resetSubmitButton();
        showError('Failed to check status: ' + error.message);
    }
}

// Load report
async function loadReport(jobId) {
    try {
        const response = await fetch(`/api/report/${jobId}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to load report');
        }
        
        displayReport(data.report_content);
        
        // Setup download button
        const downloadBtn = document.getElementById('download-btn');
        downloadBtn.onclick = () => downloadReport(data.report_content, data.filename);
        
    } catch (error) {
        console.error('Load report error:', error);
        showError('Failed to load report: ' + error.message);
    }
}

// Extract summary metrics from report
function extractSummaryMetrics(content) {
    const metrics = {
        recommendation: null,
        confidence: null,
        fairValue: null,
        entryMultiple: null,
        valuationVsDeal: null,
        ipoPE: null,
        ipoPriceBand: null,
        upsidePotential: null,
        riskLevel: null,
        rewardPotential: null,
        quickVerdict: null,
        factors: {}
    };
    
    // Extract recommendation
    const recMatch = content.match(/INVESTMENT RECOMMENDATION[\s\S]*?(STRONG BUY|BUY|CAUTIOUS BUY|HOLD|PASS)/i);
    if (recMatch) metrics.recommendation = recMatch[1];
    
    // Extract confidence
    const confMatch = content.match(/Confidence Level:.*?(\d+)\/10/i);
    if (confMatch) metrics.confidence = parseInt(confMatch[1]);
    
    // Extract fair value
    const fvMatch = content.match(/Recommended Fair Value.*?₹([\d,]+)\s*Cr/i);
    if (fvMatch) metrics.fairValue = fvMatch[1];
    
    // Extract entry multiple
    const emMatch = content.match(/Implied Entry Multiple.*?([\d.]+)x/i);
    if (emMatch) metrics.entryMultiple = emMatch[1];
    
    // Extract valuation vs deal
    const vdMatch = content.match(/Valuation vs Current Deal:.*?(Overvalued|Fair|Undervalued).*?([\d.]+)%/i);
    if (vdMatch) {
        metrics.valuationVsDeal = vdMatch[1];
        metrics.valuationPercent = vdMatch[2];
    }
    
    // Extract IPO P/E
    const peMatch = content.match(/Expected IPO Opening P\/E Ratio:.*?([\d.]+)x.*?([\d.]+)x/i);
    if (peMatch) metrics.ipoPE = `${peMatch[1]}x - ${peMatch[2]}x`;
    
    // Extract IPO price band
    const priceMatch = content.match(/Expected IPO Price Band.*?₹([\d,]+).*?₹([\d,]+)/i);
    if (priceMatch) metrics.ipoPriceBand = `₹${priceMatch[1]} - ₹${priceMatch[2]}`;
    
    // Extract upside potential
    const upsideMatch = content.match(/Upside Potential.*?([\d.]+)%\s*to\s*([\d.]+)%/i);
    if (upsideMatch) metrics.upsidePotential = `${upsideMatch[1]}% - ${upsideMatch[2]}%`;
    
    // Extract risk level
    const riskMatch = content.match(/Risk Level:.*?(Low|Medium|High)/i);
    if (riskMatch) metrics.riskLevel = riskMatch[1];
    
    // Extract reward potential
    const rewardMatch = content.match(/Reward Potential:.*?(High|Medium|Low)/i);
    if (rewardMatch) metrics.rewardPotential = rewardMatch[1];
    
    // Extract key factors
    const factorMatches = content.matchAll(/- \*\*([^:]+):\*\*\s*([✅⚠️❌]?\s*[^\n]+)/g);
    for (const match of factorMatches) {
        const factorName = match[1].trim();
        const factorValue = match[2].trim();
        metrics.factors[factorName] = factorValue;
    }
    
    return metrics;
}

// Display report with enhanced formatting
function displayReport(content) {
    const reportContent = document.getElementById('report-content');
    
    // Clean up any existing charts
    if (typeof destroyCharts === 'function') {
        destroyCharts();
    }
    
    // Extract summary metrics
    const metrics = extractSummaryMetrics(content);
    
    // Create summary dashboard HTML
    let summaryHTML = createSummaryDashboard(metrics, content);
    
    // Convert markdown to HTML for the rest of the report
    let html = markdownToHTML(content);
    
    // Combine summary and report
    reportContent.innerHTML = summaryHTML + html;
    
    // Show analytics section first (before charts initialization)
    const analyticsSection = document.getElementById('analytics-section');
    if (analyticsSection) {
        analyticsSection.style.display = 'block';
    }
    
    // Show report section
    reportSection.style.display = 'block';
    
    // Initialize charts and analytics after sections are visible
    // Use setTimeout to ensure DOM is ready
    setTimeout(() => {
        if (typeof initializeCharts === 'function') {
            initializeCharts(content, metrics);
        }
    }, 200);
    
    // Scroll to analytics section
    if (analyticsSection) {
        analyticsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Create summary dashboard
function createSummaryDashboard(metrics, fullContent) {
    const recColor = getRecommendationColor(metrics.recommendation);
    const riskColor = getRiskColor(metrics.riskLevel);
    const rewardColor = getRewardColor(metrics.rewardPotential);
    
    // Extract quick verdict if available
    let quickVerdict = '';
    const verdictMatch = fullContent.match(/QUICK VERDICT[\s\S]*?([^\n]+(?:\n[^\n]+){0,2})/i);
    if (verdictMatch) quickVerdict = verdictMatch[1].trim();
    
    return `
        <div class="summary-dashboard">
            <div class="summary-header">
                <h2>📊 Executive Summary Dashboard</h2>
            </div>
            
            <div class="summary-grid">
                <!-- Recommendation Card -->
                <div class="summary-card recommendation-card" style="border-left: 4px solid ${recColor};">
                    <div class="card-icon">🎯</div>
                    <div class="card-content">
                        <div class="card-label">Investment Recommendation</div>
                        <div class="card-value" style="color: ${recColor};">
                            ${metrics.recommendation || 'N/A'}
                        </div>
                        ${metrics.confidence ? `<div class="card-subtext">Confidence: ${metrics.confidence}/10</div>` : ''}
                    </div>
                </div>
                
                <!-- Valuation Card -->
                <div class="summary-card">
                    <div class="card-icon">💰</div>
                    <div class="card-content">
                        <div class="card-label">Fair Value</div>
                        <div class="card-value">
                            ${metrics.fairValue ? `₹${metrics.fairValue} Cr` : 'N/A'}
                        </div>
                        ${metrics.entryMultiple ? `<div class="card-subtext">Entry Multiple: ${metrics.entryMultiple}x</div>` : ''}
                        ${metrics.valuationVsDeal ? `<div class="card-subtext" style="color: ${metrics.valuationVsDeal === 'Overvalued' ? '#ef4444' : metrics.valuationVsDeal === 'Undervalued' ? '#10b981' : '#64748b'};">
                            ${metrics.valuationVsDeal} ${metrics.valuationPercent ? `by ${metrics.valuationPercent}%` : ''}
                        </div>` : ''}
                    </div>
                </div>
                
                <!-- IPO Prediction Card -->
                <div class="summary-card">
                    <div class="card-icon">📈</div>
                    <div class="card-content">
                        <div class="card-label">IPO Price Prediction</div>
                        ${metrics.ipoPE ? `<div class="card-value">P/E: ${metrics.ipoPE}</div>` : ''}
                        ${metrics.ipoPriceBand ? `<div class="card-subtext">Price Band: ${metrics.ipoPriceBand}</div>` : ''}
                        ${metrics.upsidePotential ? `<div class="card-subtext" style="color: #10b981;">Upside: ${metrics.upsidePotential}</div>` : ''}
                    </div>
                </div>
                
                <!-- Risk-Reward Card -->
                <div class="summary-card">
                    <div class="card-icon">🎲</div>
                    <div class="card-content">
                        <div class="card-label">Risk-Reward</div>
                        <div class="risk-reward-row">
                            ${metrics.riskLevel ? `<div class="risk-reward-item">
                                <span class="risk-reward-label">Risk:</span>
                                <span class="risk-reward-value" style="color: ${riskColor};">${metrics.riskLevel}</span>
                            </div>` : ''}
                            ${metrics.rewardPotential ? `<div class="risk-reward-item">
                                <span class="risk-reward-label">Reward:</span>
                                <span class="risk-reward-value" style="color: ${rewardColor};">${metrics.rewardPotential}</span>
                            </div>` : ''}
                        </div>
                    </div>
                </div>
            </div>
            
            ${quickVerdict ? `
            <div class="quick-verdict">
                <h3>🎯 Quick Verdict</h3>
                <p>${quickVerdict}</p>
            </div>
            ` : ''}
            
            ${Object.keys(metrics.factors).length > 0 ? `
            <div class="key-factors">
                <h3>✅ Key Decision Factors</h3>
                <div class="factors-grid">
                    ${Object.entries(metrics.factors).map(([key, value]) => {
                        const icon = value.includes('✅') ? '✅' : value.includes('⚠️') ? '⚠️' : value.includes('❌') ? '❌' : '•';
                        const color = value.includes('✅') ? '#10b981' : value.includes('⚠️') ? '#f59e0b' : value.includes('❌') ? '#ef4444' : '#64748b';
                        return `
                            <div class="factor-item" style="border-left: 3px solid ${color};">
                                <span class="factor-icon">${icon}</span>
                                <div class="factor-content">
                                    <div class="factor-name">${key}</div>
                                    <div class="factor-value">${value.replace(/[✅⚠️❌]/g, '').trim()}</div>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
            ` : ''}
        </div>
        
        <div class="report-divider"></div>
    `;
}

// Get recommendation color
function getRecommendationColor(recommendation) {
    if (!recommendation) return '#64748b';
    const rec = recommendation.toUpperCase();
    if (rec.includes('STRONG BUY') || rec.includes('BUY')) return '#10b981';
    if (rec.includes('CAUTIOUS')) return '#f59e0b';
    if (rec.includes('HOLD')) return '#64748b';
    return '#ef4444';
}

// Get risk color
function getRiskColor(riskLevel) {
    if (!riskLevel) return '#64748b';
    const risk = riskLevel.toUpperCase();
    if (risk === 'LOW') return '#10b981';
    if (risk === 'MEDIUM') return '#f59e0b';
    return '#ef4444';
}

// Get reward color
function getRewardColor(rewardPotential) {
    if (!rewardPotential) return '#64748b';
    const reward = rewardPotential.toUpperCase();
    if (reward === 'HIGH') return '#10b981';
    if (reward === 'MEDIUM') return '#f59e0b';
    return '#ef4444';
}

// Convert markdown to HTML
function markdownToHTML(content) {
    let html = content;
    
    // Convert markdown headers (in order of specificity)
    html = html.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    
    // Convert bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert italic
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Convert lists
    html = html.replace(/^\d+\.\s+(.*$)/gim, '<li>$1</li>');
    html = html.replace(/^[-*]\s+(.*$)/gim, '<li>$1</li>');
    
    // Wrap consecutive list items in ul/ol
    html = html.replace(/(<li>.*<\/li>\n?)+/g, function(match) {
        return '<ul>' + match + '</ul>';
    });
    
    // Convert line breaks (but preserve paragraphs)
    html = html.replace(/\n\n+/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    
    // Wrap in paragraphs
    html = '<p>' + html + '</p>';
    
    // Clean up empty paragraphs and fix headers
    html = html.replace(/<p><h([1-4])>/g, '<h$1>');
    html = html.replace(/<\/h([1-4])><\/p>/g, '</h$1>');
    html = html.replace(/<p><ul>/g, '<ul>');
    html = html.replace(/<\/ul><\/p>/g, '</ul>');
    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p><br><\/p>/g, '');
    html = html.replace(/<p>\s*<\/p>/g, '');
    
    return html;
}

// Download report
function downloadReport(content, filename) {
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || 'PreIPO_Diligence_Report.md';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Show error
function showError(message) {
    const errorContent = document.getElementById('error-content');
    errorContent.textContent = message;
    errorSection.style.display = 'block';
    errorSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Hide error
function hideError() {
    errorSection.style.display = 'none';
}

// Reset submit button
function resetSubmitButton() {
    submitBtn.disabled = false;
    submitBtn.querySelector('.btn-text').style.display = 'inline';
    submitBtn.querySelector('.btn-loader').style.display = 'none';
}

// Health check on load
window.addEventListener('load', async function() {
    try {
        const response = await fetch('/api/health');
        if (!response.ok) {
            console.warn('Server health check failed');
        }
    } catch (error) {
        console.warn('Failed to connect to server:', error);
    }
});
