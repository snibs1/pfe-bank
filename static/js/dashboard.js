

document.addEventListener('DOMContentLoaded', function() {
    initializeRiskTrendChart();
    updateSystemMetrics();
    
    setInterval(updateSystemMetrics, 3000);
});


function initializeRiskTrendChart() {
    const ctx = document.getElementById('riskTrendChart');
    
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin'],
            datasets: [{
                label: 'Vecteur de Risque',
                data: [20, 25, 22, 48, 38, 55],
                borderColor: '#0066FF',
                backgroundColor: 'rgba(0, 102, 255, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                pointHoverRadius: 8,
                pointHoverBackgroundColor: '#0066FF',
                pointHoverBorderColor: '#FFFFFF',
                pointHoverBorderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: '#131827',
                    titleColor: '#FFFFFF',
                    bodyColor: '#94A3B8',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            return 'Risque: ' + context.parsed.y + '%';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94A3B8',
                        font: {
                            size: 12
                        },
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#94A3B8',
                        font: {
                            size: 12
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}


function updateSystemMetrics() {
    
    const cpu = 35 + Math.random() * 15;
    updateMetric('cpuUsage', 'cpuBar', cpu);
    
    
    const ram = 60 + Math.random() * 15;
    updateMetric('ramUsage', 'ramBar', ram);
    
    
    const storage = 50 + Math.random() * 10;
    updateMetric('storageUsage', 'storageBar', storage);
}

function updateMetric(labelId, barId, value) {
    const rounded = Math.round(value);
    const label = document.getElementById(labelId);
    const bar = document.getElementById(barId);
    
    if (label) label.textContent = rounded + '%';
    if (bar) bar.style.width = rounded + '%';
}


const menuToggle = document.querySelector('.menu-toggle');
const sidebar = document.querySelector('.sidebar');

if (menuToggle && sidebar) {
    menuToggle.addEventListener('click', function() {
        sidebar.classList.toggle('active');
    });
}