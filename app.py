import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-bolao-2026'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'bolao.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    points_total = db.Column(db.Integer, default=0)
    bets = db.relationship('Bet', backref='user', lazy=True)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_a = db.Column(db.String(50), nullable=False)
    team_b = db.Column(db.String(50), nullable=False)
    score_a = db.Column(db.Integer, nullable=True) # Placar Real
    score_b = db.Column(db.Integer, nullable=True) # Placar Real
    date = db.Column(db.String(10), nullable=True)
    time = db.Column(db.String(5), nullable=True)
    round_no = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='aberto') # aberto / encerrado
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
    bet_a, bet_b = bet.bet_score_a, bet.bet_score_b
    # 1. Placar Exato (10 pts)
    if bet_a == real_a and bet_b == real_b:
        return 10
    # 2. Acertou Vencedor + Saldo de Gols (7 pts)
    if (real_a - real_b) == (bet_a - bet_b) and (real_a > real_b and bet_a > bet_b or real_a < real_b and bet_a < bet_b):
        return 7
    # 3. Acertou apenas Vencedor ou Empate (5 pts)
    if (real_a > real_b and bet_a > bet_b) or (real_a < real_b and bet_a < bet_b) or (real_a == real_b and bet_a == bet_b):
        return 5
    return 0

# --- ROTAS ---

@app.route('/')
@login_required
def index():
    games = Game.query.order_by(Game.date, Game.time).all()
    user_bets = {bet.game_id: bet for bet in current_user.bets}
    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template('index.html', games=games, user_bets=user_bets, current_dt=now_dt)

@app.route('/ranking')
@login_required
def ranking():
    users = User.query.order_by(User.points_total.desc()).all()
    return render_template('ranking.html', users=users)

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if current_user.username != 'admin':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Se for cadastro de novo jogo
        if 'team_a' in request.form:
            novo = Game(team_a=request.form['team_a'], team_b=request.form['team_b'], 
                        date=request.form['date'], time=request.form['time'], round_no=request.form['round_no'])
            db.session.add(novo)
        
        # Se for encerramento de jogo e cálculo de pontos
        elif 'game_id' in request.form:
            g = Game.query.get(request.form['game_id'])
            g.score_a = int(request.form['res_a'])
            g.score_b = int(request.form['res_b'])
            g.status = 'encerrado'
            
            for b in g.bets:
                pts = calcular_pontos(b, g.score_a, g.score_b)
                b.points_earned = pts
                b.user.points_total += pts
        
        db.session.commit()
        return redirect(url_for('admin'))

    games = Game.query.all()
    return render_template('admin.html', games=games)

# Mantenha as funções de Login/Logout e setup_database de antes...
