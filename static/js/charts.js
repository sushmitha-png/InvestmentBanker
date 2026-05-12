// Chart instances storage
let chartInstances = {};

// Extract financial data from report content for charts
function extractChartData(content) {
    const data = {
        valuation: { low: null, base: null, high: null },
        financials: {
            revenue_latest: null,
            revenue_forward: null,
            ebitda_forward: null,
            ebitda_margin: null,
            net_debt: null
        },
        growth: {
            revenue_cagr: null,
            ebitda_cagr: null
        },
        market: {
            listed_multiple: null,
            transaction_multiple: null,
            entry_multiple: null
        }
    };
    
    // Extract valuation - use more flexible pattern
    const valMatch = content.match(/VALUATION[\s\S]*?EV[\s\S]*?mn[\s\S]*?Low Case:[\s]*([\d,]+|N\/A)[\s\S]*?Base Case:[\s]*([\d,]+|N\/A)[\s\S]*?High Case:[\s]*([\d,]+|N\/A)/i);
    if (valMatch && valMatch[1] !== 'N/A' && valMatch[2] !== 'N/A' && valMatch[3] !== 'N/A') {
        data.valuation.low = parseFloat(valMatch[1].replace(/,/g, '')) || null;
        data.valuation.base = parseFloat(valMatch[2].replace(/,/g, '')) || null;
        data.valuation.high = parseFloat(valMatch[3].replace(/,/g, '')) || null;
    }
    
    // Extract financial metrics
    const revLatestMatch = content.match(/Latest Revenue:[\s]*([\d,]+)/i);
    if (revLatestMatch) data.financials.revenue_latest = parseFloat(revLatestMatch[1].replace(/,/g, ''));
    
    const revForwardMatch = content.match(/Forward Revenue:[\s]*([\d,]+)/i);
    if (revForwardMatch) data.financials.revenue_forward = parseFloat(revForwardMatch[1].replace(/,/g, ''));
    
    const ebitdaMatch = content.match(/Forward EBITDA:[\s]*([\d,]+)/i);
    if (ebitdaMatch) data.financials.ebitda_forward = parseFloat(ebitdaMatch[1].replace(/,/g, ''));
    
    const marginMatch = content.match(/EBITDA Margin:[\s]*([\d.]+)%?/i);
    if (marginMatch) data.financials.ebitda_margin = parseFloat(marginMatch[1]);
    
    const debtMatch = content.match(/Net Debt:[\s]*([\d,]+)/i);
    if (debtMatch) data.financials.net_debt = parseFloat(debtMatch[1].replace(/,/g, ''));
    
    // Extract growth metrics
    const revCagrMatch = content.match(/Revenue CAGR:[\s]*([\d.]+)%?/i);
    if (revCagrMatch) data.growth.revenue_cagr = parseFloat(revCagrMatch[1]);
    
    const ebitdaCagrMatch = content.match(/EBITDA CAGR:[\s]*([\d.]+)%?/i);
    if (ebitdaCagrMatch) data.growth.ebitda_cagr = parseFloat(ebitdaCagrMatch[1]);
    
    // Extract market multiples
    const listedMultMatch = content.match(/Listed Median Multiple:[\s]*([\d.]+)x?/i);
    if (listedMultMatch) data.market.listed_multiple = parseFloat(listedMultMatch[1]);
    
    const transMultMatch = content.match(/Transaction Median Multiple:[\s]*([\d.]+)x?/i);
    if (transMultMatch) data.market.transaction_multiple = parseFloat(transMultMatch[1]);
    
    const entryMultMatch = content.match(/Entry Multiple:[\s]*([\d.]+)x?/i);
    if (entryMultMatch) data.market.entry_multiple = parseFloat(entryMultMatch[1]);
    
    return data;
}

// Create valuation chart
function createValuationChart(data) {
    const ctx = document.getElementById('valuation-chart');
    const container = ctx ? ctx.closest('.chart-container') : null;
    
    if (!ctx || !container) {
        if (container) container.style.display = 'none';
        return false;
    }
    
    // Check if we have any valuation data
    if (!data.valuation.base && !data.valuation.low && !data.valuation.high) {
        container.style.display = 'none';
        return false;
    }
    
    // Show container and create chart
    container.style.display = 'block';
    
    // Destroy existing chart if any
    if (chartInstances.valuation) {
        chartInstances.valuation.destroy();
    }
    
    // Use available data, default to 0 if missing
    const low = data.valuation.low || 0;
    const base = data.valuation.base || 0;
    const high = data.valuation.high || 0;
    
    chartInstances.valuation = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Low Case', 'Base Case', 'High Case'],
            datasets: [{
                label: 'Enterprise Value (INR mn)',
                data: [
                    low / 1000,
                    base / 1000,
                    high / 1000
                ],
                backgroundColor: [
                    'rgba(239, 68, 68, 0.7)',
                    'rgba(37, 99, 235, 0.7)',
                    'rgba(16, 185, 129, 0.7)'
                ],
                borderColor: [
                    'rgb(239, 68, 68)',
                    'rgb(37, 99, 235)',
                    'rgb(16, 185, 129)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'EV: ₹' + context.parsed.y.toFixed(1) + ' Cr';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Enterprise Value (INR Cr)'
                    }
                }
            }
        }
    });
    
    return true;
}

// Create financial metrics chart
function createFinancialMetricsChart(data) {
    const ctx = document.getElementById('financial-metrics-chart');
    const container = ctx ? ctx.closest('.chart-container') : null;
    
    if (!ctx || !container) {
        if (container) container.style.display = 'none';
        return false;
    }
    
    if (chartInstances.financial) {
        chartInstances.financial.destroy();
    }
    
    const metrics = [];
    const values = [];
    const colors = [];
    
    if (data.financials.revenue_latest) {
        metrics.push('Revenue (Latest)');
        values.push(data.financials.revenue_latest / 1000);
        colors.push('rgba(59, 130, 246, 0.7)');
    }
    
    if (data.financials.revenue_forward) {
        metrics.push('Revenue (Forward)');
        values.push(data.financials.revenue_forward / 1000);
        colors.push('rgba(37, 99, 235, 0.7)');
    }
    
    if (data.financials.ebitda_forward) {
        metrics.push('EBITDA (Forward)');
        values.push(data.financials.ebitda_forward / 1000);
        colors.push('rgba(16, 185, 129, 0.7)');
    }
    
    if (data.financials.net_debt) {
        metrics.push('Net Debt');
        values.push(data.financials.net_debt / 1000);
        colors.push('rgba(239, 68, 68, 0.7)');
    }
    
    if (metrics.length === 0) {
        container.style.display = 'none';
        return false;
    }
    
    // Show container and create chart
    container.style.display = 'block';
    
    chartInstances.financial = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: metrics,
            datasets: [{
                label: 'Amount (INR Cr)',
                data: values,
                backgroundColor: colors,
                borderColor: colors.map(c => c.replace('0.7', '1')),
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return '₹' + context.parsed.y.toFixed(1) + ' Cr';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Amount (INR Cr)'
                    }
                }
            }
        }
    });
    
    return true;
}

// Create market comparables chart
function createCompsChart(data) {
    const ctx = document.getElementById('comps-chart');
    const container = ctx ? ctx.closest('.chart-container') : null;
    
    if (!ctx || !container) {
        if (container) container.style.display = 'none';
        return false;
    }
    
    if (chartInstances.comps) {
        chartInstances.comps.destroy();
    }
    
    const labels = [];
    const values = [];
    
    if (data.market.transaction_multiple) {
        labels.push('Transaction Median');
        values.push(data.market.transaction_multiple);
    }
    
    if (data.market.entry_multiple) {
        labels.push('Entry Multiple');
        values.push(data.market.entry_multiple);
    }
    
    if (data.market.listed_multiple) {
        labels.push('Listed Median');
        values.push(data.market.listed_multiple);
    }
    
    if (labels.length === 0) {
        container.style.display = 'none';
        return false;
    }
    
    // Show container and create chart
    container.style.display = 'block';
    
    chartInstances.comps = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'EV/EBITDA Multiple',
                data: values,
                backgroundColor: [
                    'rgba(245, 158, 11, 0.7)',
                    'rgba(37, 99, 235, 0.7)',
                    'rgba(16, 185, 129, 0.7)'
                ],
                borderColor: [
                    'rgb(245, 158, 11)',
                    'rgb(37, 99, 235)',
                    'rgb(16, 185, 129)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.parsed.y.toFixed(1) + 'x';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'EV/EBITDA Multiple'
                    }
                }
            }
        }
    });
}

// Create growth analysis chart
function createGrowthChart(data) {
    const ctx = document.getElementById('growth-chart');
    const container = ctx ? ctx.closest('.chart-container') : null;
    
    if (!ctx || !container) {
        if (container) container.style.display = 'none';
        return false;
    }
    
    if (chartInstances.growth) {
        chartInstances.growth.destroy();
    }
    
    const labels = [];
    const values = [];
    
    if (data.growth.revenue_cagr) {
        labels.push('Revenue CAGR');
        values.push(data.growth.revenue_cagr);
    }
    
    if (data.growth.ebitda_cagr) {
        labels.push('EBITDA CAGR');
        values.push(data.growth.ebitda_cagr);
    }
    
    if (labels.length === 0) {
        container.style.display = 'none';
        return false;
    }
    
    // Show container and create chart
    container.style.display = 'block';
    
    chartInstances.growth = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Growth Rate (%)',
                data: values,
                backgroundColor: [
                    'rgba(139, 92, 246, 0.7)',
                    'rgba(236, 72, 153, 0.7)'
                ],
                borderColor: [
                    'rgb(139, 92, 246)',
                    'rgb(236, 72, 153)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.parsed.y.toFixed(1) + '%';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Growth Rate (%)'
                    }
                }
            }
        }
    });
    
    return true;
}

// Generate quick insights
function generateInsights(data, metrics) {
    const insights = [];
    
    // Valuation insight
    if (data.valuation.base) {
        const premium = data.valuation.high && data.valuation.low 
            ? ((data.valuation.high - data.valuation.low) / data.valuation.low * 100).toFixed(1)
            : null;
        if (premium) {
            insights.push({
                icon: '💰',
                title: 'Valuation Range',
                text: `Base case valuation of ₹${(data.valuation.base / 1000).toFixed(1)} Cr with ${premium}% upside potential in high case scenario.`
            });
        }
    }
    
    // Growth insight
    if (data.growth.revenue_cagr && data.growth.ebitda_cagr) {
        const operatingLeverage = data.growth.ebitda_cagr > data.growth.revenue_cagr;
        if (operatingLeverage) {
            insights.push({
                icon: '📈',
                title: 'Strong Operating Leverage',
                text: `EBITDA growing at ${data.growth.ebitda_cagr.toFixed(1)}% vs Revenue at ${data.growth.revenue_cagr.toFixed(1)}% indicates strong operating leverage and margin expansion.`
            });
        }
    }
    
    // Market positioning
    if (data.market.entry_multiple && data.market.listed_multiple) {
        const discount = ((data.market.listed_multiple - data.market.entry_multiple) / data.market.listed_multiple * 100).toFixed(1);
        if (discount > 0) {
            insights.push({
                icon: '🎯',
                title: 'Market Opportunity',
                text: `Entry multiple of ${data.market.entry_multiple.toFixed(1)}x is ${discount}% below listed median of ${data.market.listed_multiple.toFixed(1)}x, providing potential multiple expansion opportunity.`
            });
        }
    }
    
    // Margin analysis
    if (data.financials.ebitda_margin) {
        const marginLevel = data.financials.ebitda_margin >= 20 ? 'Strong' : data.financials.ebitda_margin >= 15 ? 'Good' : 'Moderate';
        insights.push({
            icon: '💎',
            title: 'Profitability',
            text: `${marginLevel} EBITDA margin of ${data.financials.ebitda_margin.toFixed(1)}% indicates ${marginLevel.toLowerCase()} operational efficiency.`
        });
    }
    
    return insights;
}

// Render insights
function renderInsights(insights) {
    const container = document.getElementById('insights-content');
    if (!container) return;
    
    if (insights.length === 0) {
        container.innerHTML = '<p>No insights available from the data.</p>';
        return;
    }
    
    container.innerHTML = insights.map(insight => `
        <div class="insight-item">
            <div class="insight-icon">${insight.icon}</div>
            <div class="insight-content">
                <div class="insight-title">${insight.title}</div>
                <div class="insight-text">${insight.text}</div>
            </div>
        </div>
    `).join('');
}

// Initialize all charts
function initializeCharts(content, metrics) {
    try {
        const chartData = extractChartData(content);
        
        // Debug: Log extracted data
        console.log('Extracted chart data:', chartData);
        
        // Create all charts
        createValuationChart(chartData);
        createFinancialMetricsChart(chartData);
        createCompsChart(chartData);
        createGrowthChart(chartData);
        
        // Generate and render insights
        const insights = generateInsights(chartData, metrics);
        renderInsights(insights);
    } catch (error) {
        console.error('Error initializing charts:', error);
    }
}

// Cleanup charts
function destroyCharts() {
    Object.values(chartInstances).forEach(chart => {
        if (chart) chart.destroy();
    });
    chartInstances = {};
}

