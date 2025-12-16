from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import mysql.connector
from mysql.connector import Error
from functools import wraps
from datetime import datetime
import re
import os
from dotenv import load_dotenv
import gunicorn

load_dotenv()

# ==================== FUNÇÕES AUXILIARES ====================

def clean_float(valor):
    """Converte string '1.200,50' ou '1200.50' para float python"""
    if not valor: return 0.0
    if isinstance(valor, (float, int)): return float(valor)
    valor = str(valor).replace('R$', '').strip()
    if ',' in valor and '.' in valor:
        valor = valor.replace('.', '').replace(',', '.')
    elif ',' in valor:
        valor = valor.replace(',', '.')
    return float(valor)

# ==================== CONFIGURAÇÃO DO FLASK ====================

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY') + str(datetime.now().timestamp())
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora

CENTRAL_CONFIG = {
    'host': os.getenv('CENTRAL_DB_HOST'),
    'user': os.getenv('CENTRAL_DB_USER'),
    'password': os.getenv('CENTRAL_DB_PASSWORD'),
    'database': os.getenv('CENTRAL_DB_NAME'),
    'port': int(os.getenv('CENTRAL_DB_PORT', 3306))
}

def validar_env():
    obrigatorias = [
        'FLASK_SECRET_KEY',
        'CENTRAL_DB_HOST',
        'CENTRAL_DB_USER',
        'CENTRAL_DB_PASSWORD',
        'CENTRAL_DB_NAME',
        'CENTRAL_DB_PORT'
    ]
    for var in obrigatorias:
        if not os.getenv(var):
            raise RuntimeError(f'Variável de ambiente ausente: {var}')

validar_env()

# Estrutura SQL para um novo banco de dados de empresa filha
SCHEMA_SQL_CONTENT = """
-- SCRIPT_EMPRESA_ESQUELETO.sql

-- Tabela de Usuários
DROP TABLE IF EXISTS `usuarios`;
CREATE TABLE `usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `usuario` varchar(50) NOT NULL,
  `senha` varchar(255) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `is_admin` tinyint(1) DEFAULT '0' COMMENT '1 para administrador da empresa, 0 para usuário comum.',
  PRIMARY KEY (`id`),
  UNIQUE KEY `usuario` (`usuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- Tabela de Produtos
DROP TABLE IF EXISTS `produtos`;
CREATE TABLE `produtos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `codigo` varchar(50) NOT NULL UNIQUE,
  `codigo_barras` varchar(100) DEFAULT NULL,
  `descricao` varchar(255) NOT NULL,
  `unidade` varchar(10) DEFAULT 'UN',
  `quantidade` decimal(10,3) NOT NULL DEFAULT '0.000',
  `preco_custo` decimal(10,2) NOT NULL DEFAULT '0.00',
  `preco_venda` decimal(10,2) NOT NULL DEFAULT '0.00',
  `ativo` tinyint(1) DEFAULT '1',
  `data_cadastro` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- Tabela de Movimentações
DROP TABLE IF EXISTS `movimentacoes`;
CREATE TABLE `movimentacoes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `produto_id` int NOT NULL,
  `tipo` ENUM('ENTRADA', 'SAIDA', 'AJUSTE', 'CONTAGEM') NOT NULL,
  `quantidade` decimal(10,3) NOT NULL,
  `usuario_id` int DEFAULT NULL,
  `data_hora` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_mov_prod_idx` (`produto_id`),
  KEY `fk_mov_user_idx` (`usuario_id`),
  CONSTRAINT `fk_mov_prod` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`),
  CONSTRAINT `fk_mov_user` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- Tabela de Itens de Contagem (para o módulo de contagem/inventário)
DROP TABLE IF EXISTS `contagem_itens`;
CREATE TABLE `contagem_itens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `produto_id` int NOT NULL,
  `quantidade` decimal(10,3) NOT NULL,
  `data_registro` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_cont_prod_idx` (`produto_id`),
  CONSTRAINT `fk_cont_prod` FOREIGN KEY (`produto_id`) REFERENCES `produtos` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- View para facilitar o cálculo do valor total de estoque
DROP VIEW IF EXISTS `vw_valor_estoque`;
CREATE VIEW `vw_valor_estoque` AS
    SELECT 
        COUNT(p.id) AS total_produtos,
        SUM(p.quantidade) AS quantidade_total,
        SUM(p.quantidade * p.preco_custo) AS valor_custo_total,
        SUM(p.quantidade * p.preco_venda) AS valor_venda_total,
        SUM(p.quantidade * (p.preco_venda - p.preco_custo)) AS lucro_potencial
    FROM produtos p
    WHERE p.ativo = true;

-- Insere um usuário administrador padrão (ex: admin/123456)
INSERT INTO `usuarios` (`usuario`, `senha`, `nome`, `ativo`, `is_admin`) 
VALUES ('admin', SHA2('123456', 256), 'Administrador Geral', 1, 1);
"""

# ==================== FUNÇÕES DE BANCO DE DADOS ====================

def conectar_banco(config):
    """Conecta a um banco de dados usando o config fornecido"""
    conn = None
    try:
        conn = mysql.connector.connect(**config)
    except Error as e:
        print(f"❌ Erro ao conectar ao MySQL: {e}")
        flash(f"Erro ao conectar ao banco de dados: {e}", 'error')
    return conn

def executar_query(config, query, params=None, fetch=False, single=False, multi=False):
    """Executa uma query e retorna resultados se for fetch=True"""
    conn = conectar_banco(config)
    if conn is None:
        return None
        
    try:
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute(query, params or ())
        
        if fetch:
            if single:
                result = cursor.fetchone()
            elif multi:
                # Usado para executar múltiplos comandos como no SCHEMA_SQL_CONTENT
                result = cursor.fetchall()
            else:
                result = cursor.fetchall()
        else:
            conn.commit()
            result = True
            
        return result
    except Error as e:
        print(f"❌ Erro ao executar query: {e}")
        # flash(f"Erro no banco de dados: {e}", 'error') # Comentado para evitar flood de flash
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def criar_estrutura_banco_empresa(config):
    """Cria o banco de dados e as tabelas para a nova empresa."""
    try:
        # Tenta criar o banco de dados (ignorando se já existir)
        db_conn_config = config.copy()
        db_name = db_conn_config.pop('database')
        db_conn = conectar_banco(db_conn_config)
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
            cursor.close()
            db_conn.close()

        # Executa o schema completo no novo banco
        executar_query(config, f"USE `{db_name}`;", fetch=False)
        executar_query(config, SCHEMA_SQL_CONTENT, fetch=False, multi=True)
        return True
    except Exception as e:
        print(f"❌ Erro ao criar estrutura do banco: {e}")
        return False

# ==================== DECORATOR DE AUTENTICAÇÃO ====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROTAS DE AUTENTICAÇÃO ====================

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('is_master'):
            return redirect(url_for('gerenciar_empresas'))
        else:
            return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        empresa_tag = request.form.get('empresa', '').lower()
        usuario = request.form['usuario']
        senha = request.form['senha']
        
        # 1. Tenta o login MASTER (tag: MASTER)
        if empresa_tag.upper() == 'MASTER':
            # ✅ USA SHA2() diretamente no MySQL
            query = "SELECT id, usuario, nome, is_master, ativo FROM usuarios WHERE usuario = %s AND senha = SHA2(%s, 256)"
            user = executar_query(CENTRAL_CONFIG, query, (usuario, senha), fetch=True, single=True)
            
            if user and user.get('ativo') and user.get('is_master'):
                session.clear()
                session['user_id'] = user['id']
                session['user_name'] = user['nome']
                session['is_master'] = True
                flash('Login Master realizado com sucesso!', 'success')
                return jsonify({'success': True, 'redirect': url_for('gerenciar_empresas')})
            else:
                return jsonify({'success': False, 'message': 'Credenciais Master inválidas ou usuário inativo.'})

        # 2. Tenta o login de EMPRESA FILHA
        # Busca a configuração do banco da empresa
        query_empresa = "SELECT * FROM empresas WHERE tag = %s AND ativo = 'S'"
        empresa_config_db = executar_query(CENTRAL_CONFIG, query_empresa, (empresa_tag,), fetch=True, single=True)

        if empresa_config_db:
            empresa_config = {
                'host': empresa_config_db['host'],
                'user': empresa_config_db['user'],
                'password': empresa_config_db['pass'],
                'database': empresa_config_db['base'],
                'port': empresa_config_db['port']
            }
            
            # ✅ USA SHA2() diretamente no MySQL
            query_usuario = "SELECT id, usuario, nome, is_admin, ativo FROM usuarios WHERE usuario = %s AND senha = SHA2(%s, 256)"
            user = executar_query(empresa_config, query_usuario, (usuario, senha), fetch=True, single=True)
            
            if user and user.get('ativo'):
                session.clear()
                session['user_id'] = user['id']
                session['user_name'] = user['nome']
                session['is_master'] = False
                session['is_admin'] = user['is_admin']
                session['empresa_tag'] = empresa_tag
                session['empresa_nome'] = empresa_config_db['descricao']
                session['empresa_config'] = empresa_config
                flash(f'Bem-vindo(a) à {session["empresa_nome"]}, {user["nome"]}!', 'success')
                return jsonify({'success': True, 'redirect': url_for('dashboard')})
            else:
                return jsonify({'success': False, 'message': 'Credenciais inválidas ou usuário inativo.'})
        
        return jsonify({'success': False, 'message': 'Empresa não encontrada ou inativa.'})

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sessão encerrada com sucesso!', 'info')
    return redirect(url_for('login'))

# ==================== ROTAS MASTER ====================

@app.route('/master/empresas')
@login_required
def gerenciar_empresas():
    if not session.get('is_master'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))

    query = "SELECT * FROM empresas"
    empresas = executar_query(CENTRAL_CONFIG, query, fetch=True)
    return render_template('gerenciar_empresas.html', empresas=empresas)

@app.route('/master/empresa/nova', methods=['GET', 'POST'])
@login_required
def empresa_nova():
    if not session.get('is_master'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        tag = request.form['tag'].lower().strip()
        descricao = request.form['descricao'].strip()
        host = request.form['host'].strip()
        port = int(request.form['port'])
        base = request.form['base'].strip()
        user = request.form['user'].strip()
        password = request.form['pass'].strip()

        admin_usuario = request.form['admin_usuario'].strip()
        admin_nome = request.form['admin_nome'].strip()
        admin_senha = request.form['admin_senha'].strip()

        if not admin_usuario or not admin_senha:
            flash('Usuário e senha do administrador são obrigatórios.', 'error')
            return render_template('empresa_form.html')

        empresa_config = {
            'host': host,
            'user': user,
            'password': password,
            'database': base,
            'port': port
        }

        # 1️⃣ Cria banco + tabelas
        if not criar_estrutura_banco_empresa(empresa_config):
            flash('Erro ao criar estrutura do banco da empresa.', 'error')
            return render_template('empresa_form.html')

        # 2️⃣ Cria ADMIN da empresa
        query_admin = """
            INSERT INTO usuarios (usuario, nome, senha, ativo, is_admin)
            VALUES (%s, %s, SHA2(%s, 256), 1, 1)
        """
        params_admin = (admin_usuario, admin_nome, admin_senha)

        if not executar_query(empresa_config, query_admin, params_admin):
            flash('Erro ao criar administrador da empresa.', 'error')
            return render_template('empresa_form.html')

        # 3️⃣ Registra empresa no banco central
        query_empresa = """
            INSERT INTO empresas (tag, descricao, host, port, user, pass, base, ativo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'S')
        """
        params_empresa = (tag, descricao, host, port, user, password, base)

        executar_query(CENTRAL_CONFIG, query_empresa, params_empresa)

        flash(f'Empresa "{descricao}" criada com sucesso!', 'success')
        return redirect(url_for('gerenciar_empresas'))

    return render_template('empresa_form.html', empresa=None)

@app.route('/master/empresa/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def empresa_editar(id):
    if not session.get('is_master'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
        
    query_select = "SELECT * FROM empresas WHERE id = %s"
    empresa = executar_query(CENTRAL_CONFIG, query_select, (id,), fetch=True, single=True)
    
    if not empresa:
        flash('Empresa não encontrada.', 'error')
        return redirect(url_for('gerenciar_empresas'))
        
    if request.method == 'POST':
        tag = request.form['tag'].lower().strip()
        descricao = request.form['descricao'].strip()
        host = request.form['host'].strip()
        port = request.form['port'].strip()
        base = request.form['base'].strip()
        user = request.form['user'].strip()
        password = request.form['pass'].strip()
        
        query_update = """
            UPDATE empresas 
            SET tag = %s, descricao = %s, host = %s, port = %s, base = %s, user = %s, pass = %s 
            WHERE id = %s
        """
        params = (tag, descricao, host, port, base, user, password, id)
        
        if executar_query(CENTRAL_CONFIG, query_update, params, fetch=False):
            flash(f'Empresa "{descricao}" atualizada com sucesso.', 'success')
            return redirect(url_for('gerenciar_empresas'))
        else:
            flash('Falha ao atualizar a empresa.', 'error')
            
    return render_template('empresa_form.html', empresa=empresa)

@app.route('/master/empresa/toggle_status/<int:id>')
@login_required
def empresa_toggle_status(id):
    if not session.get('is_master'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))

    query_select = "SELECT ativo, descricao FROM empresas WHERE id = %s"
    empresa = executar_query(CENTRAL_CONFIG, query_select, (id,), fetch=True, single=True)
    
    if not empresa:
        flash('Empresa não encontrada.', 'error')
        return redirect(url_for('gerenciar_empresas'))
        
    novo_status = 'N' if empresa['ativo'] == 'S' else 'S'
    acao = 'desativada' if novo_status == 'N' else 'ativada'
    
    query_update = "UPDATE empresas SET ativo = %s WHERE id = %s"
    
    if executar_query(CENTRAL_CONFIG, query_update, (novo_status, id), fetch=False):
        flash(f'Empresa "{empresa["descricao"]}" foi {acao} com sucesso.', 'success')
    else:
        flash(f'Falha ao {acao} a empresa.', 'error')
        
    return redirect(url_for('gerenciar_empresas'))

# ==================== ROTAS DA EMPRESA ====================

@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('is_master'):
        return redirect(url_for('gerenciar_empresas'))
        
    empresa_config = session.get('empresa_config')
    
    # 1. Obter estatísticas do estoque (usando a view)
    query_stats = "SELECT * FROM vw_valor_estoque"
    stats = executar_query(empresa_config, query_stats, fetch=True, single=True)
    
    # 2. Obter Top 5 Produtos com Menor Estoque
    query_min_stock = "SELECT id, codigo, descricao, quantidade, unidade FROM produtos WHERE ativo = 1 ORDER BY quantidade ASC LIMIT 5"
    query_min_stock = "SELECT id, codigo, descricao, quantidade, unidade FROM produtos WHERE ativo = 1 ORDER BY quantidade ASC LIMIT 5"
    min_stock_produtos = executar_query(empresa_config, query_min_stock, fetch=True)

    # 3. Obter Total de Usuários
    query_total_users = "SELECT COUNT(id) AS total_usuarios FROM usuarios WHERE ativo = 1"
    total_users = executar_query(empresa_config, query_total_users, fetch=True, single=True)
    
    if not stats:
        stats = {}

    quantidade_total = stats.get('quantidade_total') or 0
    valor_total = stats.get('valor_venda_total') or 0
    total_produtos = stats.get('total_produtos') or 0

    stats = {
        'estoque_total': round(float(quantidade_total), 3),
        'valor_total': round(float(valor_total), 2),
        'total_produtos': total_produtos,
        'total_usuarios': total_users['total_usuarios'] if total_users else 0
    }

    
    return render_template('dashboard.html', stats=stats, min_stock_produtos=min_stock_produtos)

# --- Gerenciamento de Produtos ---

@app.route('/produtos', methods=['GET'])
@login_required
def produtos():
    if session.get('is_master'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('gerenciar_empresas'))
        
    empresa_config = session.get('empresa_config')
    search = request.args.get('search', '')
    
    query = "SELECT * FROM produtos WHERE ativo = 1"
    params = []
    
    if search:
        search_like = f"%{search}%"
        query += " AND (descricao LIKE %s OR codigo LIKE %s OR codigo_barras LIKE %s)"
        params.extend([search_like, search_like, search_like])
        
    query += " ORDER BY descricao ASC"
    
    produtos = executar_query(empresa_config, query, params, fetch=True)
    return render_template('produtos.html', produtos=produtos, search=search)

@app.route('/produto/novo', methods=['GET', 'POST'])
@login_required
def produto_novo():
    if session.get('is_master'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('gerenciar_empresas'))
        
    empresa_config = session.get('empresa_config')
    
    if request.method == 'POST':
        codigo = request.form['codigo'].strip()
        ean = request.form.get('ean', '').strip()
        descricao = request.form['descricao'].strip()
        unidade = request.form.get('unidade', 'UN').strip()
        quantidade = clean_float(request.form.get('quantidade', 0))
        custo = clean_float(request.form.get('custo', 0))
        venda = clean_float(request.form.get('venda', 0))
        
        query = """
            INSERT INTO produtos 
            (codigo, codigo_barras, descricao, unidade, quantidade, preco_custo, preco_venda) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (codigo, ean, descricao, unidade, quantidade, custo, venda)
        
        if executar_query(empresa_config, query, params, fetch=False):
            flash('Produto cadastrado com sucesso!', 'success')
            return redirect(url_for('produtos'))
        else:
            flash('Falha ao cadastrar o produto. Verifique se o código interno já existe.', 'error')

    return render_template('produto_form.html', produto=None)


@app.route('/produto/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def produto_editar(id):
    if session.get('is_master'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('gerenciar_empresas'))
        
    empresa_config = session.get('empresa_config')
    
    query_select = "SELECT * FROM produtos WHERE id = %s"
    produto = executar_query(empresa_config, query_select, (id,), fetch=True, single=True)
    
    if not produto:
        flash('Produto não encontrado.', 'error')
        return redirect(url_for('produtos'))
        
    if request.method == 'POST':
        codigo = request.form['codigo'].strip()
        ean = request.form.get('ean', '').strip()
        descricao = request.form['descricao'].strip()
        unidade = request.form.get('unidade', 'UN').strip()
        quantidade = clean_float(request.form.get('quantidade', 0))
        custo = clean_float(request.form.get('custo', 0))
        venda = clean_float(request.form.get('venda', 0))
        
        query_update = """
            UPDATE produtos 
            SET codigo = %s, codigo_barras = %s, descricao = %s, unidade = %s, 
                quantidade = %s, preco_custo = %s, preco_venda = %s
            WHERE id = %s
        """
        params = (codigo, ean, descricao, unidade, quantidade, custo, venda, id)
        
        if executar_query(empresa_config, query_update, params, fetch=False):
            flash(f'Produto "{descricao}" atualizado com sucesso!', 'success')
            return redirect(url_for('produtos'))
        else:
            flash('Falha ao atualizar o produto. Verifique se o código interno já existe.', 'error')
            
    return render_template('produto_form.html', produto=produto)


@app.route('/produto/excluir/<int:id>')
@login_required
def produto_excluir(id):
    if session.get('is_master'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('gerenciar_empresas'))

    if not session.get('is_admin'):
        flash('Acesso negado. Apenas administradores podem excluir produtos.', 'error')
        return redirect(url_for('produtos'))
        
    empresa_config = session.get('empresa_config')
    
    # Exclusão lógica (ativo = 0)
    query_delete = "UPDATE produtos SET ativo = 0 WHERE id = %s"
    
    if executar_query(empresa_config, query_delete, (id,), fetch=False):
        flash('Produto excluído (inativado) com sucesso!', 'success')
    else:
        flash('Falha ao excluir (inativar) o produto.', 'error')
        
    return redirect(url_for('produtos'))

# --- Gerenciamento de Usuários (Empresa) ---

@app.route('/usuarios')
@login_required
def usuarios():
    if session.get('is_master'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('gerenciar_empresas'))
    
    if not session.get('is_admin'):
        flash('Acesso negado. Apenas administradores podem gerenciar usuários.', 'error')
        return redirect(url_for('dashboard'))
        
    empresa_config = session.get('empresa_config')
    
    query = "SELECT id, usuario, nome, is_admin, ativo FROM usuarios ORDER BY nome ASC"
    users = executar_query(empresa_config, query, fetch=True)
    return render_template('usuarios.html', usuarios=users)


@app.route('/usuario/novo', methods=['GET', 'POST'])
@login_required
def usuario_novo():
    if session.get('is_master') or not session.get('is_admin'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
        
    empresa_config = session.get('empresa_config')
    
    if request.method == 'POST':
        usuario = request.form['usuario'].strip()
        nome = request.form['nome'].strip()
        senha = request.form['senha'].strip()
        is_admin = 1 if request.form.get('is_admin') else 0
        
        if not senha:
            flash('A senha é obrigatória para um novo usuário.', 'error')
            return render_template('usuario_form.html', user=request.form, is_new=True)

        # ✅ USA SHA2() diretamente no MySQL
        query = """
            INSERT INTO usuarios 
            (usuario, nome, senha, is_admin, ativo) 
            VALUES (%s, %s, SHA2(%s, 256), %s, 1)
        """
        params = (usuario, nome, senha, is_admin)
        
        if executar_query(empresa_config, query, params, fetch=False):
            flash(f'Usuário "{nome}" cadastrado com sucesso!', 'success')
            return redirect(url_for('usuarios'))
        else:
            flash('Falha ao cadastrar o usuário. Verifique se o nome de usuário já existe.', 'error')

    return render_template('usuario_form.html', user=None, is_new=True)


@app.route('/usuario/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def usuario_editar(id):
    if session.get('is_master') or not session.get('is_admin'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
        
    empresa_config = session.get('empresa_config')
    
    query_select = "SELECT id, usuario, nome, is_admin, ativo FROM usuarios WHERE id = %s"
    user = executar_query(empresa_config, query_select, (id,), fetch=True, single=True)
    
    if not user:
        flash('Usuário não encontrado.', 'error')
        return redirect(url_for('usuarios'))
        
    if request.method == 'POST':
        usuario = request.form['usuario'].strip()
        nome = request.form['nome'].strip()
        senha = request.form.get('senha', '').strip()
        ativo = 1 if request.form.get('ativo') else 0
        is_admin = 1 if request.form.get('is_admin') else 0
        
        query_update = """
            UPDATE usuarios 
            SET usuario = %s, nome = %s, is_admin = %s, ativo = %s
        """
        params = [usuario, nome, is_admin, ativo]
        
        # ✅ USA SHA2() diretamente no MySQL se senha foi fornecida
        if senha:
            query_update += ", senha = SHA2(%s, 256)"
            params.append(senha)
            
        query_update += " WHERE id = %s"
        params.append(id)
        
        if executar_query(empresa_config, query_update, params, fetch=False):
            flash(f'Usuário "{nome}" atualizado com sucesso!', 'success')
            return redirect(url_for('usuarios'))
        else:
            flash('Falha ao atualizar o usuário. Verifique se o nome de usuário já existe.', 'error')
            
    return render_template('usuario_form.html', user=user, is_new=False)

# --- Módulo de Contagem / API ---

@app.route('/contagem')
@login_required
def contagem():
    if session.get('is_master'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('gerenciar_empresas'))
        
    empresa_config = session.get('empresa_config')
    
    # 1. Busca os itens da contagem atual
    query_itens = """
        SELECT ci.id, p.id as produto_id, p.codigo, p.descricao, ci.quantidade 
        FROM contagem_itens ci
        JOIN produtos p ON ci.produto_id = p.id
        ORDER BY ci.data_registro DESC
    """
    itens_contagem = executar_query(empresa_config, query_itens, fetch=True) or []
    
    # 2. Busca lista de produtos para a busca manual (opcional)
    query_produtos_search = "SELECT id, codigo, descricao, unidade FROM produtos WHERE ativo = 1 ORDER BY descricao ASC"
    produtos_search = executar_query(empresa_config, query_produtos_search, fetch=True) or []
    
    return render_template('contagem.html', itens_contagem=itens_contagem, produtos_search=produtos_search)

@app.route('/api/contagem/add', methods=['POST'])
@login_required
def api_contagem_add():
    """API para adicionar/atualizar um item na contagem temporária"""
    if session.get('is_master'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
        
    empresa_config = session.get('empresa_config')
    data = request.json
    
    identifier = str(data.get('identifier', '')).strip()
    identifier = re.sub(r'\D', '', identifier)

    identifier_sem_dv = identifier[:-1] if len(identifier) == 13 else identifier
    
    quantidade = clean_float(data.get('quantidade', 1))

    if not identifier or quantidade <= 0:
        return jsonify({'success': False, 'message': 'Dados inválidos.'})

    # 1. Busca o produto (pelo código ou EAN)
    query_produto = """
    SELECT id, codigo, descricao, unidade
    FROM produtos
    WHERE ativo = 1
    AND (
        codigo_barras = %s
        OR codigo_barras = %s
        OR codigo = %s
    )
    LIMIT 1
    """
    produto = executar_query(
        empresa_config,
        query_produto,
        (identifier, identifier_sem_dv, identifier),
        fetch=True,
        single=True
    )

    if not produto:
        return jsonify({'success': False, 'message': f'Produto não encontrado: {identifier}'})

    produto_id = produto['id']

    # 2. Verifica se o produto já está na contagem (contagem_itens)
    query_select_item = "SELECT id, quantidade FROM contagem_itens WHERE produto_id = %s"
    item_existente = executar_query(empresa_config, query_select_item, (produto_id,), fetch=True, single=True)

    if item_existente:
        # Atualiza a quantidade
        nova_quantidade = item_existente['quantidade'] + quantidade
        query_update = "UPDATE contagem_itens SET quantidade = %s WHERE id = %s"
        result = executar_query(empresa_config, query_update, (nova_quantidade, item_existente['id']), fetch=False)
    else:
        # Insere novo item
        query_insert = "INSERT INTO contagem_itens (produto_id, quantidade) VALUES (%s, %s)"
        result = executar_query(empresa_config, query_insert, (produto_id, quantidade), fetch=False)
    
    if result is not None:
        return jsonify({
            'success': True, 
            'message': f'Adicionado {quantidade} de {produto["descricao"]}',
            'produto': produto
        })
    else:
        return jsonify({'success': False, 'message': 'Erro ao atualizar o banco de dados.'})

@app.route('/api/contagem/list')
@login_required
def api_contagem_list():
    """API para listar os itens da contagem atual"""
    if session.get('is_master'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
        
    empresa_config = session.get('empresa_config')
    
    query = """
        SELECT ci.id, p.id as produto_id, p.codigo, p.descricao, ci.quantidade 
        FROM contagem_itens ci
        JOIN produtos p ON ci.produto_id = p.id
        ORDER BY ci.data_registro DESC
    """
    itens = executar_query(empresa_config, query, fetch=True)
    
    return jsonify({'success': True, 'itens': itens or []})

@app.route('/api/contagem/finalizar', methods=['POST'])
@login_required
def api_contagem_finalizar():
    """API para finalizar a contagem e atualizar o estoque dos produtos contados."""
    if session.get('is_master'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
        
    empresa_config = session.get('empresa_config')
    user_id = session.get('user_id')

    # 1. Recupera todos os itens da contagem
    query_itens = "SELECT produto_id, quantidade FROM contagem_itens"
    itens = executar_query(empresa_config, query_itens, fetch=True)
    
    if not itens:
        return jsonify({'success': False, 'message': 'Nenhum item na contagem para finalizar.'})

    conn = conectar_banco(empresa_config)
    if not conn:
        return jsonify({'success': False, 'message': 'Erro de conexão com o banco.'})

    try:
        cursor = conn.cursor()
        
        # 2. Atualiza o estoque e registra as movimentações
        for item in itens:
            produto_id = item['produto_id']
            nova_quantidade = item['quantidade']
            
            # Atualiza o estoque do produto
            query_update_estoque = "UPDATE produtos SET quantidade = %s WHERE id = %s"
            cursor.execute(query_update_estoque, (nova_quantidade, produto_id))
            
            # Registra movimentação de CONTAGEM
            query_mov = """
                INSERT INTO movimentacoes 
                (produto_id, tipo, quantidade, usuario_id, data_hora)
                VALUES (%s, 'CONTAGEM', %s, %s, NOW())
            """
            cursor.execute(query_mov, (produto_id, nova_quantidade, user_id))
            
        # 3. Limpa a tabela de contagem temporária
        query_limpar = "DELETE FROM contagem_itens"
        cursor.execute(query_limpar)
        
        conn.commit()
        return jsonify({'success': True, 'total_itens': len(itens)})
        
    except Error as e:
        conn.rollback()
        print(f"❌ Erro ao finalizar contagem: {e}")
        return jsonify({'success': False, 'message': f'Erro ao salvar a contagem: {e}'})
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# --- Histórico de Movimentações ---

@app.route('/movimentacoes')
@login_required
def movimentacoes():
    """Histórico de movimentações de estoque"""
    if session.get('is_master'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('gerenciar_empresas'))
    
    empresa_config = session.get('empresa_config')
    
    query = """
        SELECT m.*, p.codigo as prod_codigo, p.descricao as prod_descricao, u.usuario as usuario_nome
        FROM movimentacoes m
        JOIN produtos p ON m.produto_id = p.id
        LEFT JOIN usuarios u ON m.usuario_id = u.id
        ORDER BY m.data_hora DESC
        LIMIT 100
    """
    movs = executar_query(empresa_config, query, fetch=True)
    return render_template('movimentacoes.html', movimentacoes=movs)

# ==================== FILTROS DE TEMPLATE ====================

@app.template_filter('currency')
def currency_filter(value):
    """Formata valor como moeda brasileira"""
    try:
        return f"R$ {float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return "R$ 0,00"

@app.template_filter('datetime_format')
def datetime_filter(value, format="%d/%m/%Y %H:%M:%S"):
    """Formata timestamp ou datetime object"""
    if isinstance(value, datetime):
        return value.strftime(format)
    # Tenta converter string/timestamp para datetime
    try:
        dt_obj = datetime.strptime(str(value).split('.')[0], '%Y-%m-%d %H:%M:%S')
        return dt_obj.strftime(format)
    except:
        return str(value)


if __name__ == '__main__':
    app.run()
