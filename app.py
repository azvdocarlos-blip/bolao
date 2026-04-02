import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///bolao.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS ---
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
    status = db.Column(db.String(20), default='aberto')
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

def calcular_pontos(bet, real_a, real_b):
    if bet.bet_score_a == real_a and bet.bet_score_b == real_b: return 10
    if (real_a > real_b and bet.bet_score_a > bet.bet_score_b) or \
       (real_a < real_b and bet.bet_score_a < bet.bet_score_b) or \
       (real_a == real_b and bet.bet_score_a == bet.bet_score_b): return 5
    return 0

# --- ROTAS ---
@app.route('/')
def index():
    games = Game.query.filter_by(status='aberto').all()
    # Envia a data atual para o
