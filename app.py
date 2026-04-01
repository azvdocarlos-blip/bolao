import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-bolao-2026'

# Configuração de caminho absoluto para o SQLite no Render
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'bolao.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS DO BANCO DE DADOS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    points_total = db.Column(db.Integer, default=0)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_a = db.Column(db.String(50))
    team_b = db.Column(db.String(50))
    score_a = db.Column(db.Integer, nullable=True)
    score_b = db.Column(db.Integer, nullable=True)
    round_no = db.Column(db.Integer)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- INICIALIZAÇÃO AUTOMÁTICA (USUÁRIO E JOGOS) ---
with app.app_context():
    db.create_all()
    
    # Criar Admin se não existir
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('123')
        admin = User(username='admin', password=hashed_pw)
        db.session.add(admin)
        db.session.commit()
    
    # Criar Jogo de Test
