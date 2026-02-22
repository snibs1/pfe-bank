

function generatePDF(clientName, dateStr) {
    
    const element = document.getElementById('pdfContent');
    
    
    const opt = {
        margin: 0.5,
        filename: `Rapport_${clientName}_${dateStr}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { 
            scale: 2, 
            useCORS: true, 
            backgroundColor: '#0A0E1A' 
        },
        jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
    };
    
    
    html2pdf().set(opt).from(element).save();
}