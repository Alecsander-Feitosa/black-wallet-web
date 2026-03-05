from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from web3 import Web3
from datetime import datetime
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'black_wallet_ultra_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blackwallet_v2.db'
db = SQLAlchemy(app)

# --- CONFIGURAÇÃO LOGIN ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- CONFIGURAÇÃO WEB3 ---
# Em vez de http://127.0.0.1:8545
provider_url = os.getenv('WEB3_PROVIDER_URL', 'http://127.0.0.1:8545')
w3 = Web3(Web3.HTTPProvider(provider_url))
USDT_ADDR = w3.to_checksum_address('0xdAC17F958D2ee523a2206206994597C13D831ec7')
abi = json.loads('[{"constant":true,"inputs":[{"name":"who","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[],"type":"function"}]')
usdt_contract = w3.eth.contract(address=USDT_ADDR, abi=abi)

# --- MODELOS DO BANCO DE DADOS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password_hash = db.Column(db.String(150))
    wallet_address = db.Column(db.String(42), unique=True)
    private_key = db.Column(db.String(100))
    transactions = db.relationship('Transaction', backref='owner', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tx_hash = db.Column(db.String(100), unique=True)
    type = db.Column(db.String(20)) # 'Recebido' ou 'Enviado'
    amount = db.Column(db.String(50))
    date = db.Column(db.String(50))
    to_address = db.Column(db.String(42))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
    # 1. Busca Saldo Real na Blockchain
    try:
        raw_balance = usdt_contract.functions.balanceOf(current_user.wallet_address).call()
        balance = "{:,.2f}".format(raw_balance / 10**6)
    except:
        balance = "0.00"

    # Troque order_ref por order_by
    user_txs = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.id.desc()).all()
    
    return render_template('index.html', endereco=current_user.wallet_address, saldo=balance, transacoes=user_txs)

@app.route('/enviar', methods=['POST'])
@login_required
def enviar():
    dest = request.form.get('destino')
    val = request.form.get('quantidade')

    try:
        # Lógica Web3 de envio
        amount_wei = int(float(val) * 10**6)
        nonce = w3.eth.get_transaction_count(current_user.wallet_address)
        
        tx = usdt_contract.functions.transfer(w3.to_checksum_address(dest), amount_wei).build_transaction({
            'chainId': w3.eth.chain_id, 'gas': 100000, 'gasPrice': w3.eth.gas_price, 'nonce': nonce,
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, current_user.private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction).hex()

        # --- SALVA NO HISTÓRICO REAL ---
        new_tx = Transaction(
            tx_hash=tx_hash,
            type='Enviado',
            amount=f"- {val}",
            date=datetime.now().strftime("%d %b, %H:%M"),
            to_address=dest,
            user_id=current_user.id
        )
        db.session.add(new_tx)
        db.session.commit()

        flash('Transferência realizada com sucesso!', 'sucesso')
    except Exception as e:
        flash(f'Erro: {str(e)}', 'erro')

    return redirect(url_for('dashboard'))

@app.route('/transaction/<tx_id>')
@login_required
def transaction_details(tx_id):
    # Busca a transação real no banco pelo Hash ou ID
    tx = Transaction.query.filter_by(tx_hash=tx_id).first()
    if not tx:
        tx = Transaction.query.get(tx_id)
    return render_template('details.html', tx=tx)

# --- LOGIN E LOGOUT (Simplificados) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for('unlock'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- INICIALIZAÇÃO ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Cria o arquivo .db do zero
        
        if not User.query.filter_by(username='alecsander').first():
            # Criação do perfil
            u = User(username='alecsander', password_hash=generate_password_hash('senha123'), 
                     wallet_address='0xD59c4Bc80af0AA88deAcD8F9255eb64D2D5D055D', # Seu endereço fixo
                     private_key='0x32F036bE2ddc89857C3487D2c6c9f7F5dbefB547')
            db.session.add(u)
            db.session.commit()
            
            # --- TRANSAÇÕES INVENTADAS (Diferentes valores e datas) ---
            t1 = Transaction(tx_hash="0x111...", type='Recebido', amount="+ 27.654.983,00", date="10 Fev, 09:41", to_address=u.wallet_address, user_id=u.id)
            t2 = Transaction(tx_hash="0x222...", type='Enviado', amount="- 1.500,00", date="15 Fev, 14:20", to_address="0xABC...", user_id=u.id)
            t3 = Transaction(tx_hash="0x333...", type='Recebido', amount="+ 45.000,00", date="01 Mar, 11:15", to_address=u.wallet_address, user_id=u.id)
            t4 = Transaction(tx_hash="0x444...", type='Enviado', amount="- 320,50", date="04 Mar, 22:10", to_address="0xXYZ...", user_id=u.id)
            
            db.session.add_all([t1, t2, t3, t4])
            db.session.commit()
            
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

