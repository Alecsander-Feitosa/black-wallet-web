import os
import json
import requests
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from web3 import Web3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'

# --- CONFIGURAÇÃO DA BASE DE DADOS ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'blackwallet_v2.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- CONFIGURAÇÃO DO LOGIN ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- CONFIGURAÇÃO WEB3 ---
provider_url = os.getenv('WEB3_PROVIDER_URL', 'https://cloudflare-eth.com')
w3 = Web3(Web3.HTTPProvider(provider_url))

USDT_ADDR = w3.to_checksum_address('0xdAC17F958D2ee523a2206206994597C13D831ec7')
abi = json.loads('[{"constant":true,"inputs":[{"name":"who","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[],"type":"function"}]')
usdt_contract = w3.eth.contract(address=USDT_ADDR, abi=abi)

# --- MODELOS DA BASE DE DADOS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password_hash = db.Column(db.String(150))
    wallet_address = db.Column(db.String(42), unique=True)
    private_key = db.Column(db.String(100))
    transactions = db.relationship('Transaction', backref='user', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tx_hash = db.Column(db.String(100), unique=True)
    type = db.Column(db.String(20)) 
    amount = db.Column(db.String(50))
    date = db.Column(db.String(50))
    to_address = db.Column(db.String(42))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- ROTAS ---
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/unlock')
@login_required
def unlock():
    return render_template('unlock.html')

@app.route('/dashboard')
@login_required
def dashboard():
    total_usdt = 28569766.81
    endereco_visivel = current_user.wallet_address # Agora mostra o endereço do usuário logado

    transacoes = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.id.desc()).all()
    
    chart_labels = ['Hoje']
    chart_data = [total_usdt]
    temp_balance = total_usdt

    for tx in transacoes:
        valor_str = tx.amount.replace('+', '').replace('-', '').replace('.', '').replace(',', '.')
        try:
            valor_float = float(valor_str.strip())
            if 'Recebido' in tx.type:
                temp_balance -= valor_float
            else:
                temp_balance += valor_float
            
            dia_mes = tx.date.split(',')[0] if ',' in tx.date else tx.date
            chart_labels.insert(0, dia_mes)
            chart_data.insert(0, temp_balance)
        except:
            continue

    precos = {}
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=tether,bitcoin,ethereum&vs_currencies=brl"
        response = requests.get(url, timeout=5)
        data = response.json()
        precos = {
            'brl': f"R$ {total_usdt * data['tether']['brl']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            'btc': f"{(total_usdt * data['tether']['brl']) / data['bitcoin']['brl']:.6f} BTC",
            'eth': f"{(total_usdt * data['tether']['brl']) / data['ethereum']['brl']:.6f} ETH"
        }
    except Exception as e:
        precos = {'brl': 'Indisponível', 'btc': '--', 'eth': '--'}

    saldo_formatado = f"{total_usdt:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    return render_template('index.html', 
                           saldo=saldo_formatado, 
                           endereco=endereco_visivel,
                           transacoes=transacoes,
                           precos=precos,
                           chart_labels=chart_labels, 
                           chart_data=chart_data)

# --- NOVA ROTA DE TRANSFERÊNCIA COM PÁGINA EXCLUSIVA ---
@app.route('/transferir', methods=['GET', 'POST'])
@login_required
def transferir():
    if request.method == 'POST':
        dest = request.form.get('destino')
        val = request.form.get('quantidade')

        try:
            val_float = float(val)
            amount_formatado = f"{val_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            # 1. TENTATIVA DE GERAR UM HASH REALISTA
            # Se não houver ETH real, criamos um Hash de simulação que parece real
            import hashlib
            import time
            simulated_hash = "0x" + hashlib.sha256(f"{dest}{val}{time.time()}".encode()).hexdigest()

            # 2. SALVAR NA BASE DE DADOS (Simulando o sucesso)
            new_tx = Transaction(
                tx_hash=simulated_hash, 
                type='Enviado', 
                amount=f"- {amount_formatado}", 
                date=datetime.now().strftime("%d %b, %H:%M"), 
                to_address=dest, 
                user_id=current_user.id
            )
            db.session.add(new_tx)
            db.session.commit()

            # 3. EXIBIR A ANIMAÇÃO DE 5.5 SEGUNDOS
            return render_template('processing_tx.html', tx_hash=simulated_hash)
            
        except Exception as e:
            flash(f'Erro Crítico de Protocolo: {str(e)}', 'erro')

    return render_template('transfer.html', endereco=current_user.wallet_address)


@app.route('/transaction/<tx_id>')
@login_required
def transaction_details(tx_id):
    tx = Transaction.query.filter_by(tx_hash=tx_id).first()
    return render_template('details.html', tx=tx)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for('unlock'))
        flash('Usuário ou senha inválidos', 'erro')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
        
        # Verifica ou cria o usuário principal
        u = User.query.filter_by(username='66281966').first()
        if not u:
            u = User(username='66281966', 
                     password_hash=generate_password_hash('senha123'), 
                     wallet_address='0xD59c4Bc80af0AA88deAcD8F9255eb64D2D5D055D', 
                     private_key='0x32F036bE2ddc89857C3487D2c6c9f7F5dbefB547')
            db.session.add(u)
            db.session.commit()
            
        # Verifica ou cria a carteira Bonelaria
        u2 = User.query.filter_by(username='bonelaria').first()
        if not u2:
            u2 = User(username='bonelaria', 
                      password_hash=generate_password_hash('senha123'), 
                      wallet_address='0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB', 
                      private_key='0x1111111111111111111111111111111111111111111111111111111111111111')
            db.session.add(u2)
            db.session.commit()
            
        # Injeção de Histórico (apenas se houver menos de 4 transações)
        if Transaction.query.filter_by(user_id=u.id).count() < 4:
            Transaction.query.filter_by(user_id=u.id).delete()
            db.session.commit()
            txs = [
                Transaction(tx_hash="0x1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s01", type='Recebido', amount="+ 30.000.000,00", date="15 Jan, 10:30", to_address=u.wallet_address, user_id=u.id),
                Transaction(tx_hash="0x4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1a2b02", type='Enviado', amount="- 1.500.000,00", date="28 Jan, 14:15", to_address="0x88a...3f1", user_id=u.id),
                Transaction(tx_hash="0x7g8h9i0j1k2l3m4n5o6p7q8r9s0t1a2b3c4d5e03", type='Recebido', amount="+ 400.000,00", date="10 Fev, 09:20", to_address=u.wallet_address, user_id=u.id),
                Transaction(tx_hash="0x111a60b2a4d5e6f7g8h9i0j1k2l3m4n5o6p7q804", type='Enviado', amount="- 250.233,19", date="25 Fev, 16:45", to_address="0x444...b2a", user_id=u.id),
                Transaction(tx_hash="0x999b55abc1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o05", type='Enviado', amount="- 80.000,00", date="05 Mar, 11:10", to_address="0x123...abc", user_id=u.id)
            ]
            for t in txs:
                db.session.add(t)
            db.session.commit()

    # Configuração de porta para o Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
