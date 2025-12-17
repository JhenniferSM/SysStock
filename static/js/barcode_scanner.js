let cameraActive = false;
window.contagemItens = []; 
let isProcessing = false;
let lastCode = '';
let lastCodeTime = 0;
const DEBOUNCE_TIME = 800;

let requestInProgress = false;

function toggleCamera() {
    const btn = document.getElementById('btnCamera');
    const status = document.getElementById('statusCamera');
    const overlay = document.getElementById('camera-overlay');
    const interactive = document.querySelector('#interactive');

    if (!cameraActive) {
        if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
            alert('⚠️ A câmera exige HTTPS.');
            return;
        }

        status.textContent = "Inicializando...";
        
        Quagga.init({
            inputStream: {
                name: "Live",
                type: "LiveStream",
                target: interactive,
                constraints: {
                    facingMode: "environment",
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                },
                area: { top: "0%", right: "0%", left: "0%", bottom: "0%" }
            },
            locator: { patchSize: "medium", halfSample: true },
            numOfWorkers: navigator.hardwareConcurrency || 4,
            decoder: {
                readers: [
                    "ean_reader", "ean_8_reader", "code_128_reader", 
                    "code_39_reader", "upc_reader"
                ]
            },
            locate: true,
            frequency: 15
        }, function (err) {
            if (err) {
                status.textContent = "Erro: " + err.name;
                return;
            }
            Quagga.start();
            cameraActive = true;
            status.textContent = "✓ Ativa";
            status.style.color = "lightgreen";
            overlay.style.display = 'block';
            btn.textContent = "⏸️ Parar Scanner";
        });

        Quagga.onDetected(function (result) {
            if (isProcessing || requestInProgress) return;
            const code = String(result.codeResult.code).trim();
            if (!code || code.length < 3) return;
            
            const qtdInput = document.getElementById('inputQtd');
            const quantidade = qtdInput ? parseFloat(qtdInput.value) || 1 : 1;
            processarCodigo(code, quantidade);
        });
        
    } else {
        Quagga.stop();
        cameraActive = false;
        status.textContent = "Inativa";
        status.style.color = "yellow";
        overlay.style.display = 'none';
        btn.textContent = "▶️ Ligar Câmera";
    }
}

function processarCodigo(code, quantidade) {
    const currentTime = Date.now();
    if (code === lastCode && (currentTime - lastCodeTime) < DEBOUNCE_TIME) return;
    
    lastCode = code;
    lastCodeTime = currentTime;
    isProcessing = true;
    adicionarItemApi(code, quantidade);
}

function adicionarItemApi(identifier, quantidade) {
    if (requestInProgress) return;
    requestInProgress = true;
    
    fetch('/api/contagem/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: identifier, quantidade: quantidade })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            beep();
            flashMensagem(data.message, 'success');
            if (typeof window.fetchItensContagem === 'function') {
                window.fetchItensContagem();
            }
        } else {
            flashMensagem(data.message, 'error');
        }
    })
    .finally(() => {
        isProcessing = false;
        requestInProgress = false;
    });
}

function atualizarTabelaContagem(itens) {
    const tabelaBody = document.querySelector('#tabelaContagem tbody');
    if (!tabelaBody) return;

    tabelaBody.innerHTML = '';
    window.contagemItens = itens;
    
    if (!itens || itens.length === 0) {
        tabelaBody.innerHTML = '<tr><td colspan="4" style="text-align:center;">📦 Vazio</td></tr>';
        return;
    }

    itens.sort((a, b) => (b.id || 0) - (a.id || 0));

    itens.forEach(item => {
        const row = tabelaBody.insertRow();
        row.innerHTML = `
            <td>${item.codigo}</td>
            <td>${item.descricao}</td>
            <td style="font-weight:bold;">${Number(item.quantidade).toFixed(3)}</td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="removerItemLocal('${item.codigo}')">🗑️</button>
            </td>
        `;
    });
}

function removerItemLocal(codigo) {
    if (!confirm(`Zerar o item ${codigo}?`)) return;

    const item = window.contagemItens.find(i => String(i.codigo) === String(codigo));
    if (!item) {
        flashMensagem('❌ Item não encontrado na lista. Tente atualizar.', 'error');
        return;
    }

    fetch('/api/contagem/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ identifier: String(codigo), quantidade: -item.quantidade })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            flashMensagem('✅ Item zerado!', 'success');
            window.fetchItensContagem();
        }
    });
}

function finalizarContagem() {
    if (!contagemItens || contagemItens.length === 0) {
        alert('❌ Nenhum item na lista para finalizar.');
        return;
    }
    
    if (!confirm(`⚠️ ATENÇÃO!\n\nVocê vai finalizar a contagem de ${contagemItens.length} produtos.\nIsso irá SUBSTITUIR as quantidades no estoque principal.\n\nDeseja continuar?`)) {
        return;
    }

    const btnFinalizar = document.getElementById('btnFinalizar');
    const textoOriginal = btnFinalizar.textContent;
    btnFinalizar.disabled = true;
    btnFinalizar.textContent = '⏳ Salvando... Aguarde';
    
    console.log(`💾 Finalizando contagem: ${contagemItens.length} itens`);
    
    fetch('/api/contagem/finalizar', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log(`✅ Contagem finalizada: ${data.total_itens} itens`);
            flashMensagem(`✅ Contagem finalizada! ${data.total_itens} produtos atualizados.`, 'success');
            contagemItens = [];
            atualizarTabelaContagem(contagemItens);
        } else {
            console.error("❌ Erro ao finalizar:", data.message);
            flashMensagem(`❌ ${data.message}`, 'error');
        }
    })
    .catch(err => {
        console.error("❌ Erro ao finalizar:", err);
        flashMensagem(`❌ Erro: ${err.message}`, 'error');
    })
    .finally(() => {
        btnFinalizar.disabled = false;
        btnFinalizar.textContent = textoOriginal;
    });
}

// Som de beep
function beep() {
    try {
        const context = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = context.createOscillator();
        const gainNode = context.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(context.destination);
        
        oscillator.type = "sine";
        oscillator.frequency.value = 880;
        gainNode.gain.value = 0.15;
        
        oscillator.start();
        setTimeout(() => oscillator.stop(), 120);
    } catch(e) {
        console.log("🔇 Beep não disponível:", e.message);
    }
}

// Flash message
function flashMensagem(message, category) {
    const mainContainer = document.querySelector('main.container');
    if (!mainContainer) return;
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${category}`;
    alertDiv.textContent = message;
    alertDiv.style.animation = 'slideIn 0.3s ease-out';
    
    mainContainer.insertBefore(alertDiv, mainContainer.firstChild);

    setTimeout(() => {
        alertDiv.style.transition = 'opacity 0.5s';
        alertDiv.style.opacity = '0';
        setTimeout(() => alertDiv.remove(), 500);
    }, 4000);
}

function diagnosticarSistema() {
    console.log("=== DIAGNÓSTICO DO SISTEMA ===");
    console.log("🌐 Protocolo:", location.protocol);
    console.log("🏠 Hostname:", location.hostname);
    console.log("📱 User Agent:", navigator.userAgent);
    console.log("🎥 MediaDevices:", !!navigator.mediaDevices);
    console.log("🔐 HTTPS:", location.protocol === 'https:');
    console.log("==============================");
}

diagnosticarSistema();