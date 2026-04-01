from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma-chave-bem-segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bolao.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS DO BANCO DE DATAS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    points_total = db.Column(db.Integer, default=0)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_a = db.Column(db.String(50))
    team_b = db.Column(db.String(50))
    score_a = db.Column(db.Integer, nullable=True) # Resultado real
    score_b = db.Column(db.Integer, nullable=True)
    round_no = db.Column(db.Integer)

class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    bet_a = db.Column(db.Integer)
    bet_b = db.Column(db.Integer)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- LÓGICA DE PONTUAÇÃO ---
def calculate_points(bet_a, bet_b, real_a, real_b):
    if bet_a == real_a and bet_b == real_b:
        return 5  # Placar Exato
    
    # Lógica de Vencedor/Empate
    res_bet = (bet_a > bet_b) - (bet_a < bet_b)
    res_real = (real_a > real_b) - (real_a < real_b)
    
    if res_bet == res_real:
        return 3
    return 0

# --- ROTAS ---
@app.route('/')
@login_required
def index():
    games = Game.query.all()
    return render_template('index.html', games=games)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Login inválido')
    return render_template('login.html')

@app.route('/ranking')
def ranking():
    users = User.query.order_by(User.points_total.desc()).all()
    return render_template('ranking.html', users=users)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
