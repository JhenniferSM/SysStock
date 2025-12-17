let cameraActive = false;
let contagemItens = [];
let isProcessing = false;
let lastCode = '';
let lastCodeTime = 0;
const DEBOUNCE_TIME = 1500; // 1.5 segundos

// Variável global para controlar a quantidade de requisições simultâneas
let requestInProgress = false;

function toggleCamera() {
    const btn = document.getElementById('btnCamera');
    const status = document.getElementById('statusCamera');
    const overlay = document.getElementById('camera-overlay');
    const interactive = document.querySelector('#interactive');

    if (!cameraActive) {
        // Verifica se está em HTTPS ou localhost
        if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
            alert('⚠️ ATENÇÃO: A câmera só funciona em HTTPS!\n\nVerifique se seu site no Render está usando HTTPS.');
            return;
        }

        // INICIAR CÂMERA
        status.textContent = "Inicializando...";
        status.style.color = "orange";
        
        Quagga.init({
            inputStream: {
                name: "Live",
                type: "LiveStream",
                target: interactive,
                constraints: {
                    facingMode: "environment",
                    focusMode: "continuous",
                    width: { min: 640, ideal: 1280, max: 1920 },
                    height: { min: 480, ideal: 720, max: 1080 },
                    aspectRatio: { ideal: 16/9 }
                },
                area: {
                    top: "15%",
                    right: "10%",
                    left: "10%",
                    bottom: "15%"
                }
            },
            locator: {
                patchSize: "medium",
                halfSample: true
            },
            numOfWorkers: navigator.hardwareConcurrency || 4,
            decoder: {
                readers: [
                    "ean_reader",
                    "ean_8_reader",
                    "code_128_reader"
                ],
                multiple: false
            },
            locate: true,
            frequency: 10
        }, function (err) {
            if (err) {
                console.error("❌ Erro ao iniciar Quagga:", err);
                status.textContent = "Erro: " + err.name;
                status.style.color = "red";
                btn.textContent = "▶️ Ligar Câmera";
                
                if (err.name === 'NotAllowedError') {
                    alert('❌ Permissão de câmera negada!\n\nVá nas configurações do navegador e permita o acesso à câmera.');
                } else if (err.name === 'NotFoundError') {
                    alert('❌ Câmera não encontrada!\n\nVerifique se seu dispositivo tem uma câmera disponível.');
                } else {
                    alert('❌ Erro ao iniciar câmera: ' + err.message);
                }
                return;
            }
            
            console.log("✅ Quagga iniciado com sucesso");
            Quagga.start();
            cameraActive = true;
            status.textContent = "✓ Ativa e Pronta";
            status.style.color = "lightgreen";
            overlay.style.display = 'block';
            btn.textContent = "⏸️ Parar Scanner";
        });

        // Handler de detecção de código
        Quagga.onDetected(function (result) {
            if (isProcessing || requestInProgress) {
                console.log("⏳ Processamento em andamento, ignorando leitura...");
                return;
            }

            const code = String(result.codeResult.code).trim();
            
            // Validação básica do código
            if (!code || code.length < 3) {
                console.log("❌ Código inválido ou muito curto:", code);
                return;
            }
            
            const qtdInput = document.getElementById('inputQtd');
            const quantidade = qtdInput ? parseFloat(qtdInput.value) || 1 : 1;
            
            console.log(`📷 Código detectado: ${code} | Qtd: ${quantidade}`);
            processarCodigo(code, quantidade);
        });
        
    } else {
        // PARAR CÂMERA
        console.log("⏹️ Parando câmera...");
        Quagga.stop();
        cameraActive = false;
        status.textContent = "Inativa";
        status.style.color = "yellow";
        overlay.style.display = 'none';
        btn.textContent = "▶️ Ligar Câmera";
    }
}

// Função de debounce e processamento do código
function processarCodigo(code, quantidade) {
    const currentTime = new Date().getTime();

    // Debounce: Ignora leituras repetidas em curto período
    if (code === lastCode && (currentTime - lastCodeTime) < DEBOUNCE_TIME) {
        console.log(`⏭️ Código ${code} ignorado (debounce)`);
        return;
    }
    
    lastCode = code;
    lastCodeTime = currentTime;
    isProcessing = true;
    
    console.log(`🔄 Processando código: ${code}`);
    adicionarItemApi(code, quantidade);
}

// Função para chamar a API e adicionar o item
function adicionarItemApi(identifier, quantidade) {
    if (requestInProgress) {
        console.warn("⚠️ Requisição já em andamento, aguarde...");
        return;
    }

    requestInProgress = true;
    const startTime = Date.now();
    
    console.log(`📤 Enviando para API: ${identifier} | Qtd: ${quantidade}`);
    
    fetch('/api/contagem/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            identifier: identifier, 
            quantidade: quantidade 
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw new Error(err.message || `Erro ${response.status}`) });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            beep();
            console.log("✅ Sucesso:", data.message);
            flashMensagem(data.message, 'success');
            fetchItensContagem(); 
            
        } else {
            console.error("❌ Erro da API:", data.message);
            flashMensagem(data.message || 'Produto não encontrado', 'error');
        }
    })
    .catch(err => {
        console.error("❌ Erro de rede ou processamento:", err);
        flashMensagem(`Erro: ${err.message}`, 'error');
    })
    .finally(() => {
        isProcessing = false;
        requestInProgress = false;
        const elapsed = Date.now() - startTime;
        console.log(`⏱️ Ciclo finalizado em ${elapsed}ms`);
    });
}
// Atualiza a tabela com os itens contados
function atualizarTabelaContagem(itens) {
    const tabelaBody = document.querySelector('#tabelaContagem tbody');
    if (!tabelaBody) {
        console.warn("⚠️ Tabela de contagem não encontrada");
        return;
    }

    tabelaBody.innerHTML = '';
    window.contagemItens = itens;
    
    if (!itens || itens.length === 0) {
        tabelaBody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px; color:#999;">📦 Comece a escanear ou buscar produtos!</td></tr>';
        return;
    }

    // Ordena por ID (mais recente primeiro)
    itens.sort((a, b) => (b.id || 0) - (a.id || 0));

    itens.forEach(item => {
        const row = tabelaBody.insertRow();
        row.innerHTML = `
            <td><strong>${item.codigo}</strong></td>
            <td>${item.descricao}</td>
            <td style="font-weight:bold; color:#667eea;">${Number(item.quantidade).toFixed(3)}</td>
            <td>
                <button class="btn btn-danger btn-sm" 
                        onclick="removerItemLocal('${item.codigo}')"
                        title="Zerar este item da contagem">
                    🗑️ Zerar
                </button>
            </td>
        `;
    });
    
    console.log(`📊 Tabela atualizada: ${itens.length} itens`);
}

// Remove item da contagem (zera)
function removerItemLocal(codigo) {
    if (!confirm(`Confirma zerar o item ${codigo} da contagem temporária?`)) {
        return;
    }

    const item = contagemItens.find(i => i.codigo === codigo);
    if (!item) {
        flashMensagem('❌ Item não encontrado na lista local', 'error');
        return;
    }

    console.log(`🗑️ Zerando item: ${codigo} (qtd: ${item.quantidade})`);

    fetch('/api/contagem/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            identifier: String(codigo),
            quantidade: -item.quantidade
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log("✅ Item zerado com sucesso");
            flashMensagem('✅ Item removido da contagem!', 'success');
            contagemItens = contagemItens.filter(i => i.codigo !== codigo);
            atualizarTabelaContagem(contagemItens);
        } else {
            console.error("❌ Erro ao zerar:", data.message);
            flashMensagem(`❌ ${data.message}`, 'error');
        }
    })
    .catch(err => {
        console.error("❌ Erro de rede ao zerar:", err);
        flashMensagem('❌ Erro de comunicação', 'error');
    });
}

// Finalizar a contagem
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

// Diagnóstico do sistema
function diagnosticarSistema() {
    console.log("=== DIAGNÓSTICO DO SISTEMA ===");
    console.log("🌐 Protocolo:", location.protocol);
    console.log("🏠 Hostname:", location.hostname);
    console.log("📱 User Agent:", navigator.userAgent);
    console.log("🎥 MediaDevices:", !!navigator.mediaDevices);
    console.log("🔐 HTTPS:", location.protocol === 'https:');
    console.log("==============================");
}

// Executa diagnóstico ao carregar
diagnosticarSistema();