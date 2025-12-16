let cameraActive = false;
let contagemItens = []; // Lista local de itens contados
let isProcessing = false;
let lastCode = '';
let lastCodeTime = 0;
const DEBOUNCE_TIME = 1000; // 1 segundo

function toggleCamera() {
    const btn = document.getElementById('btnCamera');
    const status = document.getElementById('statusCamera');
    const overlay = document.getElementById('camera-overlay');
    const interactive = document.querySelector('#interactive');

    if (!cameraActive) {
        // INICIAR CÂMERA
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
                area: { // Define área de escaneamento
                    top: "20%",
                    right: "10%",
                    left: "10%",
                    bottom: "20%"
                }
            },
            locator: {
                patchSize: "medium",
                halfSample: true
            },
            numOfWorkers: 4,
            decoder: {
                readers: [
                    "ean_reader",
                    "ean_8_reader", 
                    "code_128_reader",
                    "code_39_reader",
                    "upc_reader",
                    "upc_e_reader"
                ],
                debug: {
                    drawBoundingBox: true,
                    showFrequency: true,
                    drawScanline: true,
                    showPattern: true
                }
            },
            locate: true
        }, function (err) {
            if (err) {
                console.error(err);
                status.textContent = "Erro ao Iniciar: " + err.name;
                status.style.color = "red";
                btn.textContent = "▶️ Ligar Câmera / Iniciar Scanner";
                return;
            }
            Quagga.start();
            cameraActive = true;
            status.textContent = "Ativa (Pronta)";
            status.style.color = "lightgreen";
            overlay.style.display = 'block';
            btn.textContent = "⏸️ Parar Scanner";
        });

        Quagga.onDetected(function (result) {
            if (isProcessing) return; // Debounce do detector

            const code = String(result.codeResult.code).trim();
            const qtdInput = document.getElementById('inputQtd');
            const quantidade = qtdInput ? parseFloat(qtdInput.value) || 1 : 1;
            processarCodigo(code, quantidade);
        });
        
    } else {
        // PARAR CÂMERA
        Quagga.stop();
        cameraActive = false;
        status.textContent = "Inativa";
        status.style.color = "yellow";
        overlay.style.display = 'none';
        btn.textContent = "▶️ Ligar Câmera / Iniciar Scanner";
    }
}

// Função de debounce e processamento do código
function processarCodigo(code, quantidade) {
    const currentTime = new Date().getTime();

    // Debounce: Ignora leituras repetidas em um curto período
    if (code === lastCode && (currentTime - lastCodeTime) < DEBOUNCE_TIME) {
        return;
    }
    
    lastCode = code;
    lastCodeTime = currentTime;
    
    // Adiciona uma contagem e trava o processamento
    isProcessing = true;
    
    adicionarItemApi(code, quantidade);
}


// Função para chamar a API e adicionar o item
function adicionarItemApi(identifier, quantidade) {
    const inputQtd = document.getElementById('inputQtd');
    
    fetch('/api/contagem/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ identifier: identifier, quantidade: quantidade })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            beep();
            console.log("✅ Adicionado/Atualizado:", data.produto.descricao, "Qtd:", quantidade);
            flashMensagem(`✅ ${data.message}`, 'success');
            
            // Atualiza a lista local e a tabela
            let itemAtualizado = false;
            for (let i = 0; i < contagemItens.length; i++) {
                if (contagemItens[i].produto_id === data.produto.id) {
                    contagemItens[i].quantidade += quantidade;
                    itemAtualizado = true;
                    break;
                }
            }
            if (!itemAtualizado) {
                // Se não encontrou, é um novo item
                contagemItens.unshift({ // Adiciona no início
                    id: Date.now(), // ID temporário para lista local
                    produto_id: data.produto.id,
                    codigo: data.produto.codigo,
                    descricao: data.produto.descricao,
                    quantidade: quantidade
                });
            }
            
            atualizarTabelaContagem(contagemItens);
            
        } else {
            console.error("❌ Produto não encontrado:", identifier);
            flashMensagem(`❌ ${data.message || 'Produto não encontrado no sistema.'}`, 'error');
        }
        isProcessing = false;
        
    })
    .catch(err => {
        console.error("❌ Erro de rede:", err);
        flashMensagem('❌ Erro de comunicação com o servidor.', 'error');
        isProcessing = false;
    });
}


// Atualiza a tabela com os itens contados (chamada pelo app.js/contagem.html)
function atualizarTabelaContagem(itens) {
    const tabelaBody = document.querySelector('#tabelaContagem tbody');
    if (!tabelaBody) return;

    tabelaBody.innerHTML = '';
    window.contagemItens = itens; // Sincroniza a lista global
    
    if (!itens || itens.length === 0) {
        tabelaBody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:15px;">Comece a escanear!</td></tr>';
        return;
    }

    // Ordena por data_registro (ou ID temporário, se for só a lista local)
    itens.sort((a, b) => (b.id || b.data_registro) - (a.id || a.data_registro)); 

    itens.forEach(item => {
        const row = tabelaBody.insertRow();
        row.innerHTML = `
            <td>${item.codigo}</td>
            <td>${item.descricao}</td>
            <td style="font-weight:bold;">${item.quantidade}</td>
            <td>
               <button class="btn btn-danger btn-sm"
                onclick="removerItemLocal(${item.produto_id}, '${item.codigo}', ${item.quantidade})"
                Zerar
                </button>
            </td>
        `;
    });
}

function removerItemLocal(produtoId, codigo, quantidade) {
    if (!confirm(`Tem certeza que deseja zerar o item ${codigo} da contagem?`)) {
        return;
    }

    fetch('/api/contagem/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            identifier: String(codigo),
            quantidade: -quantidade
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            flashMensagem('Item zerado na contagem temporária!', 'info');
            contagemItens = contagemItens.filter(item => item.produto_id !== produtoId);
            atualizarTabelaContagem(contagemItens);
        } else {
            flashMensagem(`❌ Erro ao zerar: ${data.message}`, 'error');
        }
    })
    .catch(err => {
        console.error("❌ Erro ao zerar:", err);
        flashMensagem('Erro de comunicação ao zerar o item.', 'error');
    });
}

// Função para finalizar a contagem e salvar no estoque principal
function finalizarContagem() {
    if (!contagemItens || contagemItens.length === 0) {
        alert('Nenhum item na lista para finalizar.');
        return;
    }
    
    if (!confirm(`Tem certeza que deseja FINALIZAR a contagem? Isso atualizará o estoque principal de ${contagemItens.length} produtos.`)) {
        return;
    }

    const btnFinalizar = document.getElementById('btnFinalizar');
    const textoOriginal = btnFinalizar.textContent;
    btnFinalizar.disabled = true;
    btnFinalizar.textContent = 'Salvando... Aguarde.';
    
    fetch('/api/contagem/finalizar', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            flashMensagem(`✅ Contagem finalizada! ${data.total_itens} produtos atualizados no estoque.`, 'success');
            // Limpa a lista e a tabela
            contagemItens = [];
            atualizarTabelaContagem(contagemItens);
        } else {
            flashMensagem(`❌ Erro ao finalizar: ${data.message}`, 'error');
        }
        btnFinalizar.disabled = false;
        btnFinalizar.textContent = textoOriginal;
    })
    .catch(err => {
        console.error("❌ Erro ao salvar:", err);
        flashMensagem('Erro ao comunicar com o servidor!', 'error');
        btnFinalizar.disabled = false;
        btnFinalizar.textContent = textoOriginal;
    });
}

// Som de beep
function beep() {
    try {
        const context = new (window.AudioContext || window.webkitAudioContext)();
        if (!context) return;
        
        const oscillator = context.createOscillator();
        const gainNode = context.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(context.destination);
        
        oscillator.type = "square";
        oscillator.frequency.value = 660;
        gainNode.gain.value = 0.1;
        
        oscillator.start();
        setTimeout(() => {
            if (oscillator.stop) oscillator.stop();
        }, 100);
    } catch(e) {
        console.log("Beep não disponível/permitido:", e);
    }
}

// Função para exibir flash message (copiada do main.js)
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