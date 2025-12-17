from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import mysql.connector
from mysql.connector import Error
from functools import wraps
from datetime import datetime
import re
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'chave_secreta_padrao_mude_me')
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# ==================== CONEXÃO COM POOL ====================

def get_db_connection():
    """Conexão com tratamento melhorado para Railway/Render"""
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT', 3306)),
            connect_timeout=10,  # Timeout de 10 segundos
            autocommit=False,
            pool_name='sysstock_pool',
            pool_size=5,
            pool_reset_session=True
        )
        return conn
    except Error as e:
        print(f"❌ Erro de conexão MySQL: {e}")
        return None

def executar_query(query, params=None, fetch=False, single=False):
    """Executa query com tratamento de erro melhorado"""
    conn = get_db_connection()
    if conn is None:
        print("❌ Falha ao obter conexão")
        return None
    
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute(query, params or ())
        
        if fetch:
            result = cursor.fetchone() if single else cursor.fetchall()
        else:
            conn.commit()
            result = True
        
        return result
        
    except Error as e:
        print(f"❌ Erro query: {e}")
        if conn:
            conn.rollback()
        return None
        
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# ==================== UTILITÁRIOS ====================

def clean_float(valor):
    if not valor: return 0.0
    if isinstance(valor, (float, int)): return float(valor)
    valor = str(valor).replace('R$', '').strip()
    if ',' in valor and '.' in valor:
        valor = valor.replace('.', '').replace(',', '.')
    elif ',' in valor:
        valor = valor.replace(',', '.')
    return float(valor)

# ==================== DECORATORS ====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Faça login para acessar.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def master_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_master'):
            flash('Acesso restrito ao Master.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== AUTENTICAÇÃO ====================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('gerenciar_empresas') if session.get('is_master') else url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        empresa_tag = request.form.get('empresa', '').lower().strip()
        usuario = request.form.get('usuario', '').strip()
        senha = request.form.get('senha', '').strip()
        
        # LOGIN MASTER
        if empresa_tag.upper() == 'MASTER':
            query = """
                SELECT id, usuario, nome, is_master, ativo 
                FROM usuarios 
                WHERE usuario = %s AND senha = SHA2(%s, 256) AND is_master = 1
            """
            user = executar_query(query, (usuario, senha), fetch=True, single=True)
            
            if user and user['ativo']:
                session.clear()
                session['user_id'] = user['id']
                session['user_name'] = user['nome']
                session['is_master'] = True
                session['is_admin'] = True
                return jsonify({'success': True, 'redirect': url_for('gerenciar_empresas')})
            else:
                return jsonify({'success': False, 'message': 'Credenciais Master inválidas.'})

        # LOGIN EMPRESA
        query_emp = "SELECT id, descricao, ativo FROM empresas WHERE tag = %s"
        empresa = executar_query(query_emp, (empresa_tag,), fetch=True, single=True)

        if not empresa:
            return jsonify({'success': False, 'message': 'Empresa não encontrada.'})
        if empresa['ativo'] != 'S':
            return jsonify({'success': False, 'message': 'Empresa inativa.'})

        query_user = """
            SELECT id, usuario, nome, is_admin, ativo 
            FROM usuarios 
            WHERE usuario = %s AND senha = SHA2(%s, 256) AND empresa_id = %s
        """
        user = executar_query(query_user, (usuario, senha, empresa['id']), fetch=True, single=True)

        if user and user['ativo']:
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['nome']
            session['empresa_id'] = empresa['id']
            session['empresa_nome'] = empresa['descricao']
            session['is_master'] = False
            session['is_admin'] = bool(user['is_admin'])
            return jsonify({'success': True, 'redirect': url_for('dashboard')})
        else:
            return jsonify({'success': False, 'message': 'Usuário ou senha inválidos.'})

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==================== MASTER - GERENCIAR EMPRESAS ====================

@app.route('/master/empresas')
@login_required
@master_required
def gerenciar_empresas():
    query = "SELECT * FROM empresas ORDER BY id DESC"
    empresas = executar_query(query, fetch=True)
    return render_template('gerenciar_empresas.html', empresas=empresas)

@app.route('/master/empresa/nova', methods=['GET', 'POST'])
@login_required
@master_required
def empresa_nova():
    if request.method == 'POST':
        tag = request.form['tag'].lower().strip()
        descricao = request.form['descricao'].strip()
        admin_user = request.form['admin_usuario'].strip()
        admin_nome = request.form['admin_nome'].strip()
        admin_senha = request.form['admin_senha'].strip()

        conn = get_db_connection()
        if not conn:
            flash('Erro de conexão com banco de dados.', 'error')
            return redirect(url_for('gerenciar_empresas'))
            
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO empresas (tag, descricao, ativo) VALUES (%s, %s, 'S')",
                (tag, descricao)
            )
            empresa_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO usuarios (empresa_id, usuario, nome, senha, is_admin, ativo)
                VALUES (%s, %s, %s, SHA2(%s, 256), 1, 1)
            """, (empresa_id, admin_user, admin_nome, admin_senha))

            conn.commit()
            flash(f'✅ Empresa "{descricao}" criada com sucesso!', 'success')
            return redirect(url_for('gerenciar_empresas'))
        except Error as e:
            conn.rollback()
            flash(f'❌ Erro: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()

    return render_template('empresa_form.html', empresa=None)

@app.route('/master/empresa/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@master_required
def empresa_editar(id):
    if request.method == 'GET':
        query = "SELECT * FROM empresas WHERE id = %s"
        empresa = executar_query(query, (id,), fetch=True, single=True)
        if not empresa:
            flash('Empresa não encontrada.', 'error')
            return redirect(url_for('gerenciar_empresas'))
        return render_template('empresa_form.html', empresa=empresa)
    
    tag = request.form['tag'].lower().strip()
    descricao = request.form['descricao'].strip()
    
    query = "UPDATE empresas SET tag=%s, descricao=%s WHERE id=%s"
    if executar_query(query, (tag, descricao, id)):
        flash('Empresa atualizada com sucesso!', 'success')
    else:
        flash('Erro ao atualizar empresa.', 'error')
    return redirect(url_for('gerenciar_empresas'))

@app.route('/master/empresa/toggle/<int:id>')
@login_required
@master_required
def empresa_toggle_status(id):
    query = "UPDATE empresas SET ativo = IF(ativo='S', 'N', 'S') WHERE id = %s"
    executar_query(query, (id,))
    flash('Status atualizado.', 'success')
    return redirect(url_for('gerenciar_empresas'))

# ==================== DASHBOARD ====================

@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('is_master'): 
        return redirect(url_for('gerenciar_empresas'))
    
    emp_id = session['empresa_id']
    
    query_stats = """
        SELECT 
            COUNT(id) as total_produtos,
            SUM(quantidade) as estoque_total,
            SUM(quantidade * preco_venda) as valor_total
        FROM produtos 
        WHERE empresa_id = %s AND ativo = 1
    """
    stats_data = executar_query(query_stats, (emp_id,), fetch=True, single=True)
    
    query_users = "SELECT COUNT(id) as total FROM usuarios WHERE empresa_id = %s AND ativo = 1"
    total_users = executar_query(query_users, (emp_id,), fetch=True, single=True)

    stats = {
        'total_produtos': stats_data['total_produtos'] or 0,
        'estoque_total': float(stats_data['estoque_total'] or 0),
        'valor_total': float(stats_data['valor_total'] or 0),
        'total_usuarios': total_users['total'] or 0
    }

    query_min = """
        SELECT id, codigo, descricao, quantidade, unidade 
        FROM produtos 
        WHERE empresa_id = %s AND ativo = 1 
        ORDER BY quantidade ASC LIMIT 5
    """
    min_stock = executar_query(query_min, (emp_id,), fetch=True)

    return render_template('dashboard.html', stats=stats, min_stock_produtos=min_stock)

# ==================== PRODUTOS ====================

@app.route('/produtos')
@login_required
def produtos():
    if session.get('is_master'): 
        return redirect(url_for('gerenciar_empresas'))
    
    emp_id = session['empresa_id']
    search = request.args.get('search', '')
    
    query = "SELECT * FROM produtos WHERE empresa_id = %s AND ativo = 1"
    params = [emp_id]
    
    if search:
        query += " AND (descricao LIKE %s OR codigo LIKE %s OR codigo_barras LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like])
        
    query += " ORDER BY descricao ASC"
    prods = executar_query(query, tuple(params), fetch=True)
    
    return render_template('produtos.html', produtos=prods, search=search)

@app.route('/produto/novo', methods=['GET', 'POST'])
@login_required
def produto_novo():
    if session.get('is_master'): 
        return redirect(url_for('gerenciar_empresas'))
    
    if request.method == 'POST':
        emp_id = session['empresa_id']
        codigo = request.form['codigo']
        ean = request.form.get('ean')
        descricao = request.form['descricao']
        unidade = request.form.get('unidade', 'UN')
        qtd = clean_float(request.form.get('quantidade'))
        custo = clean_float(request.form.get('custo'))
        venda = clean_float(request.form.get('venda'))
        
        query = """
            INSERT INTO produtos 
            (empresa_id, codigo, codigo_barras, descricao, unidade, quantidade, preco_custo, preco_venda)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        if executar_query(query, (emp_id, codigo, ean, descricao, unidade, qtd, custo, venda)):
            flash('Produto criado!', 'success')
            return redirect(url_for('produtos'))
        else:
            flash('Erro: Código duplicado?', 'error')

    return render_template('produto_form.html', produto=None)

@app.route('/produto/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def produto_editar(id):
    emp_id = session.get('empresa_id')
    
    query_get = "SELECT * FROM produtos WHERE id = %s AND empresa_id = %s"
    produto = executar_query(query_get, (id, emp_id), fetch=True, single=True)
    
    if not produto:
        flash('Produto não encontrado.', 'error')
        return redirect(url_for('produtos'))
        
    if request.method == 'POST':
        codigo = request.form['codigo']
        ean = request.form.get('ean')
        descricao = request.form['descricao']
        unidade = request.form.get('unidade', 'UN')
        qtd = clean_float(request.form.get('quantidade'))
        custo = clean_float(request.form.get('custo'))
        venda = clean_float(request.form.get('venda'))
        
        query_upd = """
            UPDATE produtos 
            SET codigo=%s, codigo_barras=%s, descricao=%s, unidade=%s, 
                quantidade=%s, preco_custo=%s, preco_venda=%s
            WHERE id=%s AND empresa_id=%s
        """
        if executar_query(query_upd, (codigo, ean, descricao, unidade, qtd, custo, venda, id, emp_id)):
            flash('Atualizado!', 'success')
            return redirect(url_for('produtos'))
            
    return render_template('produto_form.html', produto=produto)

@app.route('/produto/excluir/<int:id>')
@login_required
def produto_excluir(id):
    if not session.get('is_admin'): 
        return redirect(url_for('produtos'))
    
    query = "UPDATE produtos SET ativo = 0 WHERE id = %s AND empresa_id = %s"
    executar_query(query, (id, session['empresa_id']))
    flash('Produto excluído.', 'success')
    return redirect(url_for('produtos'))

# ==================== USUÁRIOS ====================

@app.route('/usuarios')
@login_required
def usuarios():
    if not session.get('is_admin') or session.get('is_master'): 
        return redirect(url_for('dashboard'))
        
    query = "SELECT * FROM usuarios WHERE empresa_id = %s ORDER BY nome"
    users = executar_query(query, (session['empresa_id'],), fetch=True)
    return render_template('usuarios.html', usuarios=users)

@app.route('/usuario/novo', methods=['GET', 'POST'])
@login_required
def usuario_novo():
    if not session.get('is_admin'): 
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        usuario = request.form['usuario']
        nome = request.form['nome']
        senha = request.form['senha']
        is_admin = 1 if request.form.get('is_admin') else 0
        emp_id = session['empresa_id']
        
        query = """
            INSERT INTO usuarios (empresa_id, usuario, nome, senha, is_admin, ativo)
            VALUES (%s, %s, %s, SHA2(%s, 256), %s, 1)
        """
        if executar_query(query, (emp_id, usuario, nome, senha, is_admin)):
            flash('Usuário criado!', 'success')
            return redirect(url_for('usuarios'))
        else:
            flash('Erro: Usuário já existe.', 'error')
            
    return render_template('usuario_form.html', user=None, is_new=True)

@app.route('/usuario/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def usuario_editar(id):
    if not session.get('is_admin'): 
        return redirect(url_for('dashboard'))
    
    query_get = "SELECT * FROM usuarios WHERE id = %s AND empresa_id = %s"
    user = executar_query(query_get, (id, session['empresa_id']), fetch=True, single=True)
    
    if not user: 
        return redirect(url_for('usuarios'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        usuario = request.form['usuario']
        senha = request.form.get('senha')
        ativo = 1 if request.form.get('ativo') else 0
        is_admin = 1 if request.form.get('is_admin') else 0
        
        params = [usuario, nome, is_admin, ativo]
        query_upd = "UPDATE usuarios SET usuario=%s, nome=%s, is_admin=%s, ativo=%s"
        
        if senha:
            query_upd += ", senha=SHA2(%s, 256)"
            params.append(senha)
            
        query_upd += " WHERE id=%s AND empresa_id=%s"
        params.extend([id, session['empresa_id']])
        
        executar_query(query_upd, tuple(params))
        flash('Usuário atualizado.', 'success')
        return redirect(url_for('usuarios'))
        
    return render_template('usuario_form.html', user=user, is_new=False)

# ==================== MOVIMENTAÇÕES ====================

@app.route('/movimentacoes')
@login_required
def movimentacoes():
    query = """
        SELECT m.*, p.codigo as prod_codigo, p.descricao as prod_descricao, u.usuario as usuario_nome
        FROM movimentacoes m
        JOIN produtos p ON m.produto_id = p.id
        LEFT JOIN usuarios u ON m.usuario_id = u.id
        WHERE m.empresa_id = %s
        ORDER BY m.data_hora DESC LIMIT 100
    """
    movs = executar_query(query, (session['empresa_id'],), fetch=True)
    return render_template('movimentacoes.html', movimentacoes=movs)

# ==================== CONTAGEM (CORRIGIDO) ====================

@app.route('/contagem')
@login_required
def contagem():
    query = """
        SELECT ci.id, p.id as produto_id, p.codigo, p.descricao, ci.quantidade 
        FROM contagem_itens ci
        JOIN produtos p ON ci.produto_id = p.id
        WHERE ci.empresa_id = %s
        ORDER BY ci.data_registro DESC
    """
    itens = executar_query(query, (session['empresa_id'],), fetch=True)
    return render_template('contagem.html', itens_contagem=itens)

@app.route('/api/contagem/add', methods=['POST'])
@login_required
def api_contagem_add():
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'Dados inválidos'}), 400
            
        ident = re.sub(r'\D', '', str(data.get('identifier', '')))
        qtd = clean_float(data.get('quantidade', 1))
        emp_id = session['empresa_id']

        print(f"🔍 Buscando produto: {ident}")

        query_prod = """
            SELECT id, codigo, descricao 
            FROM produtos 
            WHERE empresa_id = %s AND ativo = 1 
            AND (codigo_barras = %s OR codigo = %s)
            LIMIT 1
        """
        prod = executar_query(query_prod, (emp_id, ident, ident), fetch=True, single=True)
        
        if not prod:
            print(f"❌ Produto não encontrado: {ident}")
            return jsonify({'success': False, 'message': f'Produto {ident} não encontrado.'}), 404

        print(f"✅ Produto encontrado: {prod['descricao']}")

        # Verifica se já existe na contagem
        check_q = "SELECT id, quantidade FROM contagem_itens WHERE produto_id = %s AND empresa_id = %s"
        existe = executar_query(check_q, (prod['id'], emp_id), fetch=True, single=True)
        
        if existe:
            nova_qtd = existe['quantidade'] + qtd
            
            # Se a quantidade ficar <= 0, remove o item
            if nova_qtd <= 0:
                executar_query("DELETE FROM contagem_itens WHERE id=%s", (existe['id'],))
                print(f"🗑️ Item removido da contagem: {prod['descricao']}")
                return jsonify({
                    'success': True, 
                    'message': f"Item {prod['codigo']} removido da contagem", 
                    'produto': prod,
                    'removed': True
                })
            else:
                executar_query("UPDATE contagem_itens SET quantidade=%s WHERE id=%s", (nova_qtd, existe['id']))
                print(f"📝 Quantidade atualizada: {nova_qtd}")
        else:
            # Novo item na contagem
            if qtd > 0:
                executar_query(
                    "INSERT INTO contagem_itens (empresa_id, produto_id, quantidade) VALUES (%s, %s, %s)",
                    (emp_id, prod['id'], qtd)
                )
                print(f"➕ Novo item adicionado: {prod['descricao']}")
            
        return jsonify({
            'success': True, 
            'message': f"✅ {prod['descricao']}", 
            'produto': prod
        })
        
    except Exception as e:
        print(f"❌ Erro no endpoint /api/contagem/add: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500

@app.route('/api/contagem/list')
@login_required
def api_contagem_list():
    try:
        query = """
            SELECT ci.id, p.id as produto_id, p.codigo, p.descricao, ci.quantidade 
            FROM contagem_itens ci
            JOIN produtos p ON ci.produto_id = p.id
            WHERE ci.empresa_id = %s
            ORDER BY ci.data_registro DESC
        """
        itens = executar_query(query, (session['empresa_id'],), fetch=True)
        return jsonify({'success': True, 'itens': itens or []})
    except Exception as e:
        print(f"❌ Erro ao listar contagem: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/contagem/finalizar', methods=['POST'])
@login_required
def api_contagem_finalizar():
    emp_id = session['empresa_id']
    user_id = session['user_id']
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Erro de conexão'}), 500
        
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT produto_id, quantidade FROM contagem_itens WHERE empresa_id = %s", (emp_id,))
        itens = cursor.fetchall()
        
        if not itens:
            return jsonify({'success': False, 'message': 'Nada para salvar.'}), 400
            
        for item in itens:
            cursor.execute(
                "UPDATE produtos SET quantidade = %s WHERE id = %s AND empresa_id = %s",
                (item['quantidade'], item['produto_id'], emp_id)
            )
            cursor.execute("""
                INSERT INTO movimentacoes (empresa_id, produto_id, tipo, quantidade, usuario_id)
                VALUES (%s, %s, 'CONTAGEM', %s, %s)
            """, (emp_id, item['produto_id'], item['quantidade'], user_id))
            
        cursor.execute("DELETE FROM contagem_itens WHERE empresa_id = %s", (emp_id,))
        conn.commit()
        
        print(f"✅ Contagem finalizada: {len(itens)} itens atualizados")
        return jsonify({'success': True, 'total_itens': len(itens)})
        
    except Error as e:
        conn.rollback()
        print(f"❌ Erro ao finalizar contagem: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ==================== FILTROS ====================

@app.template_filter('currency')
def currency_filter(value):
    try: 
        return f"R$ {float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: 
        return "R$ 0,00"

@app.template_filter('datetime_format')
def datetime_filter(value):
    try: 
        return value.strftime("%d/%m/%Y %H:%M")
    except: 
        return str(value)

if __name__ == '__main__':
    app.run(debug=True)