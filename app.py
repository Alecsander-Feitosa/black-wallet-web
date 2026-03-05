from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'black_wallet_ultra_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blackwallet_v2.db'
db = SQLAlchemy(app)

# --- CONFIGURAÇÃO LOGIN ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'

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
    # SALDO SIMULADO (Aparecerá como 27 Milhões)
    balance = "27,654,983.00"
    
    # Busca as transações salvas no banco de dados local
    user_txs = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.id.desc()).all()
    
    return render_template('index.html', endereco=current_user.wallet_address, saldo=balance, transacoes=user_txs)

@app.route('/enviar', methods=['POST'])
@login_required
def enviar():
    dest = request.form.get('destino')
    val = request.form.get('quantidade')

    # SIMULAÇÃO DE ENVIO: Apenas registra no banco de dados
    try:
        tx_hash_simulado = f"0x{os.urandom(20).hex()}..." # Gera um hash falso
        
        new_tx = Transaction(
            tx_hash=tx_hash_simulado,
            type='Enviado',
            amount=f"- {val}",
            date=datetime.now().strftime("%d %b, %H:%M"),
            to_address=dest,
            user_id=current_user.id
        )
        db.session.add(new_tx)
        db.session.commit()

        flash('Transferência enviada para processamento na rede!', 'sucesso')
    except Exception as e:
        flash(f'Erro no processamento: {str(e)}', 'erro')

    return redirect(url_for('dashboard'))

@app.route('/transaction/<tx_id>')
@login_required
def transaction_details(tx_id):
    tx = Transaction.query.filter_by(tx_hash=tx_id).first()
    if not tx:
        tx = Transaction.query.get(tx_id)
    return render_template('details.html', tx=tx)

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

# --- INICIALIZAÇÃO PARA O RENDER ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Garante que o perfil do Alecsander exista
        if not User.query.filter_by(username='alecsander').first():
            u = User(username='alecsander', password_hash=generate_password_hash('senha123'), 
                     wallet_address='0xD59c4Bc80af0AA88deAcD8F9255eb64D2D5D055D',
                     private_key='CHAVE_SIMULADA_DE_TESTE')
            db.session.add(u)
            db.session.commit()
            
            # Histórico de transações para parecer conta real
            t1 = Transaction(tx_hash="0x7a8b9c...", type='Recebido', amount="+ 27,654,983.00", date="02 Mar, 14:20", to_address=u.wallet_address, user_id=u.id)
            t2 = Transaction(tx_hash="0x1d2e3f...", type='Enviado', amount="- 1,500.00", date="04 Mar, 09:15", to_address="0xABC...123", user_id=u.id)
            
            db.session.add_all([t1, t2])
            db.session.commit()
            
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
