import os
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
    if bet.bet_score_a == real_a and bet.bet_score_b == real_b:
        return 10
    if (real_a > real_b and bet.bet_score_a > bet.bet_score_b) or \
       (real_a < real_b and bet.bet_score_a < bet.bet_score_b) or \
       (real_a == real_b and bet.bet_score_a == bet.bet_score_b):
        return 5
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
        existing_bet = Bet.query.filter_by(user_id=current_user.id, game_id=game_id).first()
        if existing_bet:
            existing_bet.bet_score_a = int(score_a)
            existing_bet.bet_score_b = int(score_b)
        else:
            nova_aposta = Bet(user_id=current_user.id, game_id=game_id, bet_score_a=int(score_a), bet_score_b=int(score_b))
            db.session.add(nova_aposta)
        db.session.commit()
        flash('Palpite registrado!')
    return redirect(url_for('index'))

@app.route('/ranking')
def ranking():
    users = User.query.order_by(User.points_total.desc()).all()
    return render_template('ranking.html', users=users)

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if current_user.username != 'admin':
        return redirect(url_for('index'))
    if request.method == 'POST':
        if 'team_a' in request.form:
            try:
                novo_jogo = Game(
                    team_a=request.form.get('team_a'),
                    team_a_flag=request.form.get('flag_a', 'br').lower(),
                    team_b=request.form.get('team_b'),
                    team_b_flag=request.form.get('flag_b', 'ar').lower(),
                    date=request.form.get('date'),
                    time=request.form.get('time'),
                    round_no=int(request.form.get('round_no', 1))
                )
                db.session.add(novo_jogo)
                db.session.commit()
                flash('✅ Jogo cadastrado!')
            except Exception as e:
                db.session.rollback()
                flash(f'❌ Erro: {str(e)}')
        elif 'game_id' in request.form:
            try:
                g = Game.query.get(request.form.get('game_id'))
                res_a = request.form.get('res_a')
                res_b = request.form.get('res_b')
                if g and res_a is not None and res_b is not None:
                    g.score_a, g.score_b, g.status = int(res_a), int(res_b), 'encerrado'
                    for b in g.bets:
                        pts = calcular_pontos(b, g.score_a, g.score_b)
                        b.points_earned = pts
                        b.user.points_total += pts
                    db.session.commit()
                    flash('🏆 Resultado lançado!')
            except Exception as e:
                db.session.rollback()
                flash(f'❌ Erro: {str(e)}')
        return redirect(url_for('admin'))
    return render_template('admin.html', games=Game.query.all())

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
