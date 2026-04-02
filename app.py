import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'

# --- CONFIGURAÇÃO DO BANCO DE DADOS (SUPABASE/RENDER) ---
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

# Se não houver URL de ambiente, usa SQLite local para testes
app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///bolao.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS DO BANCO ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    points_total = db.Column(db.Integer, default=0)
    bets = db.relationship('Bet', backref='user', lazy=True)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_a = db.Column(db.String(50), nullable=False)
    team_a_flag = db.Column(db.String(10), default='br')
    team_b = db.Column(db.String(50), nullable=False)
    team_b_flag = db.Column(db.String(10), default='ar')
    score_a = db.Column(db.Integer)
    score_b = db.Column(db.Integer)
    date = db.Column(db.String(10))
    time = db.Column(db.String(5))
    round_no = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='aberto') # aberto, encerrado
    bets = db.relationship('Bet', backref='game', lazy=True)

class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    bet_score_a = db.Column(db.Integer, nullable=False)
    bet_score_b = db.Column(db.Integer, nullable=False)
    points_earned = db.Column(db.Integer, default=0)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- LÓGICA DE PONTUAÇÃO ---
def calcular_pontos(bet, real_a, real_b):
    if bet.bet_score_a == real_a and bet.bet_score_b == real_b:
        return 10  # Placar exato
    if (real_a > real_b and bet.bet_score_a > bet.bet_score_b) or \
       (real_a < real_b and bet.bet_score_a < bet.bet_score_b) or \
       (real_a == real_b and bet.bet_score_a == bet.bet_score_b):
        return 5   # Acertou o vencedor/empate
    return 0

# --- ROTAS ---
@app.route('/')
def index():
    games = Game.query.filter_by(status='aberto').all()
    return render_template('index.html', games=games)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        
        # Cria usuário admin se não existir (apenas para facilitar seu primeiro acesso)
        if username == 'admin' and not user:
            new_admin = User(username='admin', password=generate_password_hash('123'))
            db.session.add(new_admin)
            db.session.commit()
            login_user(new_admin)
            return redirect(url_for('index'))
            
        flash('Usuário ou senha inválidos')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/apostar', methods=['POST'])
@login_required
def apostar():
    game_id = request.form.get('game_id')
    score_a = request.form.get('score_a')
    score_b = request.form.get('score_b')
    
    if game_id and score_a and score_b:
        # Verifica se já existe aposta
        existing_bet = Bet.query.filter_by(user_id=current_user.id, game_id=game_id).first()
        if existing_bet:
            existing_bet.bet_score_a = int(score_a)
            existing_bet.bet_score_b = int(score_b)
        else:
            nova_aposta = Bet(
                user_id=
