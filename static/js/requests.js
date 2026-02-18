

let currentClientData = null;


function filterTable() {
    const input = document.getElementById('searchInput');
    const filter = input.value.toUpperCase();
    const table = document.getElementById('clientsTable');
    const rows = table.getElementsByTagName('tr');
    
    for (let i = 1; i < rows.length; i++) {
        const row = rows[i];
        const cells = row.getElementsByTagName('td');
        let found = false;
        
        for (let j = 0; j < cells.length; j++) {
            const cell = cells[j];
            if (cell) {
                const text = cell.textContent || cell.innerText;
                if (text.toUpperCase().indexOf(filter) > -1) {
                    found = true;
                    break;
                }
            }
        }
        
        row.style.display = found ? '' : 'none';
    }
}


function showClientModal(clientId, clientData) {
    currentClientData = clientData;
    const modal = new bootstrap.Modal(document.getElementById('clientModal'));
    
    
    const modalBody = document.getElementById('modalBody');
    
    
    const monthlyRate = clientData.interest_rate / 100 / 12;
    const nPayments = clientData.loan_term;
    let monthlyPayment = 0;
    
    if (monthlyRate > 0) {
        monthlyPayment = clientData.loan_amount * monthlyRate * Math.pow(1 + monthlyRate, nPayments) / (Math.pow(1 + monthlyRate, nPayments) - 1);
    } else {
        monthlyPayment = clientData.loan_amount / nPayments;
    }
    
    
    let riskColor, riskStatus;
    if (clientData.risk_score > 50) {
        riskColor = '#EF4444';
        riskStatus = 'Risque Élevé';
    } else if (clientData.risk_score > 30) {
        riskColor = '#F59E0B';
        riskStatus = 'Risque Modéré';
    } else {
        riskColor = '#10B981';
        riskStatus = 'Risque Faible';
    }
    
    
    const circumference = 440;
    const offset = circumference - (clientData.risk_score / 100 * circumference);
    
    modalBody.innerHTML = `
        <div class="client-info-grid">
            <div class="info-box">
                <h6><i class="bi bi-person-badge me-2"></i>Informations Client</h6>
                <div class="info-item">
                    <span class="info-label">Nom</span>
                    <span class="info-value">${clientData.client_name}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">CIN</span>
                    <span class="info-value">${clientData.cin}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Téléphone</span>
                    <span class="info-value">${clientData.phone || 'N/A'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Revenu Annuel</span>
                    <span class="info-value">${clientData.annual_income.toLocaleString()} MAD</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Score de Crédit</span>
                    <span class="info-value">${clientData.credit_score}</span>
                </div>
            </div>
            
            <div class="info-box">
                <h6><i class="bi bi-bank me-2"></i>Détails du Prêt</h6>
                <div class="info-item">
                    <span class="info-label">Montant</span>
                    <span class="info-value">${clientData.loan_amount.toLocaleString()} MAD</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Durée</span>
                    <span class="info-value">${clientData.loan_term} Mois</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Taux d'Intérêt</span>
                    <span class="info-value">${clientData.interest_rate}%</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Mensualité</span>
                    <span class="info-value">${Math.round(monthlyPayment).toLocaleString()} MAD</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Date</span>
                    <span class="info-value">${new Date(clientData.date_added).toLocaleDateString('fr-FR')}</span>
                </div>
            </div>
        </div>
        
        <div class="risk-analysis-box">
            <h6 style="color: var(--primary-blue); margin-bottom: 20px;">
                <i class="bi bi-shield-exclamation me-2"></i>Analyse de Risque IA
            </h6>
            <div class="risk-circle-container">
                <svg width="150" height="150">
                    <circle cx="75" cy="75" r="70" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="10"></circle>
                    <circle cx="75" cy="75" r="70" fill="none" stroke="${riskColor}" stroke-width="10" 
                        stroke-dasharray="${circumference}" stroke-dashoffset="${offset}" 
                        transform="rotate(-90 75 75)" style="transition: stroke-dashoffset 1s ease;">
                    </circle>
                </svg>
                <div class="risk-percentage-modal" style="color: ${riskColor};">
                    ${clientData.risk_score}%
                </div>
            </div>
            <div style="font-size: 16px; font-weight: 700; color: ${riskColor}; margin-top: 10px;">
                ${riskStatus}
            </div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 5px;">
                <i class="bi bi-cpu me-1"></i>Modèle: XGBoost v2.4
            </div>
        </div>
        
        <div class="decision-box ${clientData.status === 'Approved' ? 'approved' : 'rejected'}">
            <div class="decision-icon-large">
                <i class="bi bi-${clientData.status === 'Approved' ? 'check-circle-fill' : 'x-circle-fill'}"></i>
            </div>
            <div class="decision-title">
                ${clientData.status === 'Approved' ? 'CRÉDIT APPROUVÉ' : 'CRÉDIT REFUSÉ'}
            </div>
            <div class="decision-description">
                ${clientData.status === 'Approved' 
                    ? 'Le profil du client présente un niveau de risque acceptable. Le dossier de crédit peut être approuvé selon les conditions standards de la banque.' 
                    : 'Le profil présente un risque élevé (' + clientData.risk_score + '%). Facteurs: ratio dette/revenu élevé ou score de crédit insuffisant. Une révision manuelle est recommandée.'}
            </div>
        </div>
    `;
    
    modal.show();
}


function downloadPDF() {
    if (!currentClientData) return;
    
    
    const element = document.createElement('div');
    element.style.padding = '40px';
    element.style.backgroundColor = '#0A0E1A';
    element.style.color = '#FFFFFF';
    element.innerHTML = document.getElementById('modalBody').innerHTML;
    document.body.appendChild(element);
    
    const opt = {
        margin: 0.5,
        filename: `Rapport_${currentClientData.client_name}_${currentClientData.id}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: '#0A0E1A' },
        jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
    };
    
    html2pdf().set(opt).from(element).save().then(() => {
        document.body.removeChild(element);
    });
}