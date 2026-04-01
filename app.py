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

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_a = db.Column(db.String(50), nullable=False)
    team_b = db.Column(db.String(50), nullable=False)
    score_a = db.Column(db.Integer, nullable=True)
    score_b = db.Column(db.Integer, nullable=True)
    date = db.Column(db.String(10), nullable=True) # Formato: YYYY-MM-DD
    time = db.Column(db.String(5), nullable=True)  # Formato: HH:MM
    round_no = db.Column(db.Integer, default=1)

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
    return render_template('index.html', games=games)

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    # Segurança: Só o usuário 'admin' acessa esta página
    if current_user.username != 'admin':
        flash('Acesso negado!')
        return redirect(url_for('index'))

    if request.method == 'POST':
        novo_jogo = Game(
            team_a=request.form['team_a'],
            team_b=request.form['team_b'],
            date=request.form['date'],
            time=request.form['time'],
            round_no=request.form['round_no']
        )
        db.session.add(novo_jogo)
        db.session.commit()
        flash('Jogo cadastrado com sucesso!')
        return redirect(url_for('admin'))

    games = Game.query.all()
    return render_template('admin.html', games=games)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Usuário ou senha incorretos.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
