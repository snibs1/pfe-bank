
document.addEventListener('DOMContentLoaded', function() {
    
    const clientId = 'CL-' + Math.floor(100000 + Math.random() * 900000);
    const clientIdEl = document.getElementById('clientId');
    const clientIdField = document.getElementById('clientIdField');
    
    if (clientIdEl) clientIdEl.textContent = clientId;
    if (clientIdField) clientIdField.value = clientId;
    
    
    autoFillInterestRate();
    
    
    const creditInput = document.querySelector('input[name="credit_score"]');
    if(creditInput) {
        creditInput.addEventListener('input', (e) => updateScoreBar(e.target.value));
    }
});


function autoFillInterestRate() {
    const map = { 'Personal': 7.5, 'Business': 5.25, 'Home': 4.2, 'Car': 6.5, 'Education': 3.5 };
    const select = document.querySelector('select[name="loan_purpose"]');
    const input = document.querySelector('input[name="interest_rate"]');
    if(select && input) {
        input.value = map[select.value] || 5.0;
    }
}

function updateScoreBar(val) {
    const bar = document.getElementById('scoreBar');
    if(bar) {
        const pct = Math.min(100, Math.max(0, ((val - 300) / 550) * 100));
        bar.style.width = pct + "%";
    }
}


function fillSampleData() {
    console.log("Filling sample data...");
    
    const sampleData = {
        client_name: 'Ahmed Benani', 
        cin: 'AB123456', 
        phone: '0661123456',
        annual_income: 600000, 
        credit_score: 750, 
        debt_to_income_ratio: 28.5,
        loan_amount: 300000, 
        loan_term: 72, 
        interest_rate: 4.20,
        gender: 'Male', 
        marital_status: 'Married',
        loan_purpose: 'Home'
    };

    
    for (const [key, value] of Object.entries(sampleData)) {
        const input = document.querySelector(`[name="${key}"]`);
        if (input) {
            input.value = value;
            
            input.style.transition = "background 0.3s";
            input.style.backgroundColor = "rgba(56, 189, 248, 0.2)";
            setTimeout(() => input.style.backgroundColor = "", 300);
        }
    }
    
    updateScoreBar(750);
}


function resetForm() {
    if(confirm("Voulez-vous vider le formulaire ?")) {
        document.getElementById('simulationForm').reset();
        document.getElementById('resultSection').classList.add('d-none');
        updateScoreBar(0);
    }
}


const simForm = document.getElementById('simulationForm');
if (simForm) {
    simForm.onsubmit = async function(e) {
        e.preventDefault();
        
        
        const btn = this.querySelector('button[type="submit"]');
        const txt = btn.querySelector('.btn-text');
        const loader = btn.querySelector('.btn-loader');
        
        btn.disabled = true;
        txt.classList.add('d-none');
        loader.classList.remove('d-none');

        try {
            const formData = new FormData(this);
            
            
            const response = await fetch('/predict', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.error) {
                alert("Erreur: " + result.error);
            } else {
                showResults(result);
            }

        } catch (error) {
            console.error(error);
            alert("Erreur de connexion au serveur.");
        } finally {
            
            btn.disabled = false;
            txt.classList.remove('d-none');
            loader.classList.add('d-none');
        }
    };
}

function showResults(res) {
    const section = document.getElementById('resultSection');
    const riskScore = parseFloat(res.risk_score);
    
    
    const icon = document.getElementById('resultIcon');
    const title = document.getElementById('resultTitle');
    const score = document.getElementById('riskScoreDisplay');
    const badge = document.getElementById('riskCategory');
    const reason = document.getElementById('aiReason');

    
    if (res.status === 'Approved') {
        icon.innerHTML = '<i class="bi bi-check-circle-fill text-success"></i>';
        title.innerHTML = '<span class="text-success">APPROUVÉ</span>';
        title.className = "fw-800 mb-1 text-success";
        badge.className = "badge bg-success bg-opacity-25 text-success border border-success px-3 py-2";
        badge.innerText = "Risque Faible";
    } else {
        icon.innerHTML = '<i class="bi bi-x-circle-fill text-danger"></i>';
        title.innerHTML = '<span class="text-danger">REFUSÉ</span>';
        title.className = "fw-800 mb-1 text-danger";
        badge.className = "badge bg-danger bg-opacity-25 text-danger border border-danger px-3 py-2";
        badge.innerText = "Risque Élevé";
    }

    score.innerText = riskScore + "%";
    reason.innerHTML = `<strong>Analyse IA:</strong> ${res.reason}`;
    
    
    section.classList.remove('d-none');
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });

    
    const total = document.getElementById('todayAnalyses');
    if(total) total.innerText = parseInt(total.innerText) + 1;
    
    if(res.status === 'Approved') {
        const app = document.getElementById('todayApproved');
        if(app) app.innerText = parseInt(app.innerText) + 1;
    }
}