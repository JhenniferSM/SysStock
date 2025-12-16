// ==========================================
// MAIN.JS - SysStock
// Funções globais e utilitários
// ==========================================

// Função para exibir flash message
function flashMensagem(message, category) {
    const mainContainer = document.querySelector('main.container');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${category}`;
    alertDiv.textContent = message;
    
    // Adiciona o novo alerta no início do container principal
    mainContainer.insertBefore(alertDiv, mainContainer.firstChild);

    // Auto-esconder após 5 segundos
    setTimeout(() => {
        alertDiv.style.transition = 'opacity 0.5s';
        alertDiv.style.opacity = '0';
        setTimeout(() => alertDiv.remove(), 500);
    }, 5000);
}

// Auto-esconder alertas após 5 segundos
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
});

// Confirmação de exclusão
function confirmarExclusao(mensagem) {
    return confirm(mensagem || 'Tem certeza que deseja excluir?');
}

// Formatar moeda brasileira
function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor);
}

// Formatar número
function formatarNumero(valor, decimais = 2) {
    return parseFloat(valor).toFixed(decimais);
}

// Limpar formatação de float (inverso do currency_filter do Python)
function cleanFloat(valor) {
    if (!valor) return 0.0;
    valor = String(valor).replace('R$', '').trim();
    
    // Se tem vírgula e ponto, remove o ponto (separador de milhares)
    if (valor.includes(',') && valor.includes('.')) {
        valor = valor.replace(/\./g, '').replace(',', '.');
    } 
    // Se tem só vírgula, troca por ponto
    else if (valor.includes(',')) {
        valor = valor.replace(',', '.');
    }
    
    return parseFloat(valor) || 0;
}

// Validar código de barras EAN
function validarEAN(codigo) {
    if (!codigo || codigo.length !== 13) return false;
    
    let soma = 0;
    for (let i = 0; i < 12; i++) {
        const digito = parseInt(codigo[i]);
        soma += (i % 2 === 0) ? digito : digito * 3;
    }
    
    const checksum = (10 - (soma % 10)) % 10;
    return checksum === parseInt(codigo[12]);
}

// Validar formulário (Apenas para inputs required)
function validarFormulario(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    const inputs = form.querySelectorAll('input[required]');
    let valido = true;
    
    inputs.forEach(input => {
        if (!input.value) {
            valido = false;
            input.style.borderColor = 'red';
        } else {
            input.style.borderColor = '#ddd';
        }
    });
    
    if (!valido) {
        alert('Por favor, preencha todos os campos obrigatórios.');
    }
    
    return valido;
}

// Exportar dados para CSV
function exportarParaCSV(dados, nomeArquivo = 'dados.csv') {
    if (!dados || dados.length === 0) {
        alert('Não há dados para exportar!');
        return;
    }
    
    const headers = Object.keys(dados[0]);
    const csv = [
        headers.join(';'), // Cabeçalho
        ...dados.map(row => headers.map(fieldName => {
            let cell = row[fieldName] === null || row[fieldName] === undefined ? '' : String(row[fieldName]);
            cell = cell.replace(/"/g, '""'); // Escapa aspas
            if (cell.includes(';') || cell.includes('\n') || cell.includes('"')) {
                cell = `"${cell}"`; // Coloca entre aspas se tiver delimitadores
            }
            return cell;
        }).join(';'))
    ].join('\n');

    const blob = new Blob(["\ufeff", csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = nomeArquivo;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}