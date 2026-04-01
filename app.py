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
    score_a = db.Column(db.Integer, nullable=True) # Resultado Real
    score_b = db.Column(db.Integer, nullable=True) # Resultado Real
    date = db.Column(db.String(10), nullable=True) # YYYY-MM-DD
    time = db.Column(db.String(5), nullable=True)  # HH:MM
    round_no = db.Column(db.Integer, default=1)
    bets = db.relationship('Bet', backref='game', lazy=True)

class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    bet_score_a = db.Column(db.Integer, nullable=False)
    bet_score_b = db.Column(db.Integer, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- INICIALIZAÇÃO ---
with app.app_context():
    db.create_all()
    usuarios = ['admin', 'edna', 'juliano', 'william', 'dorinha']
    senha_hash = generate_password_hash('123')
    for nome in usuarios:
        if not User.query.filter_by(username=nome).first():
            db.session.add(User(username=nome, password=senha_hash))
    db.session.commit()

# --- ROTAS ---

@app.route('/')
@login_required
def index():
    games = Game.query.order_by(Game.date, Game.time).all()
    # Pega as apostas do usuário atual para mostrar no campo
    user_bets = {bet.game_id: bet for bet in current_user.bets}
    
    # Lógica de tempo para travar palpite
    now = datetime.now()
    current_dt = now.strftime("%Y-%m-%d %H:%M")
    
    return render_template('index.html', games=games, user_bets=user_bets, current_dt=current_dt)

@app.route('/palpite/<int:game_id>', methods=['POST'])
@login_required
def palpite(game_id):
    game = Game.query.get_or_404(game_id)
    
    # TRAVA DE HORÁRIO: Verifica se o jogo já começou
    game_dt = f"{game.date} {game.time}"
    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if now_dt >= game_dt:
        flash('Erro: O jogo já começou! Palpites encerrados.')
        return redirect(url_for('index'))

    score_a = request.form.get('score_a')
    score_b = request.form.get('score_b')

    # Verifica se já existe aposta, se sim atualiza, se não cria
    bet = Bet.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if bet:
        bet.bet_score_a = score_a
        bet.bet_score_b = score_b
    else:
        new_bet = Bet(user_id=current_user.id, game_id=game_id, bet_score_a=score_a, bet_score_b=score_b)
        db.session.add(new_bet)
    
    db.session.commit()
    flash('Palpite salvo com sucesso!')
    return redirect(url_for('index'))

# Mantenha as rotas /admin, /login e /logout que enviamos antes...
