import os
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import dj_database_url

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bolao-militar-2026-super-secret'

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
# Tenta pegar a URL do Supabase/Render, se não houver, usa SQLite local
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = uri or 'sqlite:///' + os.path.join(basedir, 'bolao.db')
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
    score_a = db.Column(db.Integer, nullable=True)
    score_b = db.Column(db.Integer, nullable=True)
    date = db.Column(db.String(10), nullable=True) # YYYY-MM-DD
    time = db.Column(db.String(5), nullable=True)  # HH:MM
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

# --- LÓGICA DE PONTUAÇÃO ---
def calcular_pontos(bet, real_a, real_b):
    b_a, b_b = int(bet.bet_score_a), int(bet.bet_score_b)
    r_a, r_b = int(real_a), int(real_b)
    
    if b_a == r_a and b_b == r_b: return 10 # Placar Exato
    
    # Saldo de gols e vencedor
    if (r_a - r_b) == (b_a - b_b) and ((r_a > r_b and b_a > b_b) or (r_a < r_b and b_a < b_b)):
        return 7
    
    # Apenas vencedor ou empate
    if (r_a > r_b and b_a > b_b) or (r_a < r_b and b_a < b_b) or (r_a == r_b and b_a == b_b):
        return 5
        
    return 0

# --- INICIALIZAÇÃO ---
with app.app_context():
    db.create_all()
    lista_users = ['admin', 'edna', 'juliano', 'william', 'dorinha']
    senha_padrao = generate_password_hash('123')
    for nome in lista_users:
        if not User.query.filter_by(username=nome).first():
            db.session.add(User(username=nome, password=senha_padrao))
    db.session.commit()

# --- ROTAS ---

@app.route('/')
@login_required
def index():
    games = Game.query.order_by(Game.date, Game.time).all()
    user_bets = {b.game_id: b for b in current_user.bets}
    # Ajuste de Fuso Horário (GMT-3)
    now_br = datetime.now() - timedelta(hours=3)
    current_dt = now_br.strftime("%Y-%m-%d %H:%M")
    return render_template('index.html', games=games, user_bets=user_bets, current_dt=current_dt)

@app.route('/ranking')
@login_required
def ranking():
    users = User.query.order_by(User.points_total.desc()).all()
    return render_template('ranking.html', users=users)

@app.route('/palpite/<int:game_id>', methods=['POST'])
@login_required
def palpite(game_id):
    game = Game.query.get_or_404(game_id)
    now_br = datetime.now() - timedelta(hours=3)
    if now_br.strftime("%Y-%m-%d %H:%M") >= f"{game.date} {game.time}":
        flash('🚫 Tempo esgotado! O jogo já começou.')
        return redirect(url_for('index'))
    
    b_a = request.form.get('score_a')
    b_b = request.form.get('score_b')
    
    bet = Bet.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if bet:
        bet.bet_score_a, bet.bet_score_b = b_a, b_b
    else:
        db.session.add(Bet(user_id=current_user.id, game_id=game_id, bet_score_a=b_a, bet_score_b=b_b))
    
    db.session.commit()
    flash('✅ Palpite salvo com sucesso!')
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if current_user.username != 'admin':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        # Cadastro de Novo Jogo
        if 'team_a' in request.form:
            novo_jogo = Game(
                team_a=request.form['team_a'],
                team_a_flag=request.form['flag_a'].lower(),
                team_b=request.form['team_b'],
                team_b_flag=request.form['flag_b'].lower(),
                date=request.form['date'],
                time=request.form['time'],
                round_no=request.form['round_no']
            )
            db.session.add(novo_jogo)
        
        # Encerramento e Pontuação
        elif 'game_id' in request.form:
            g = Game.query.get(request.form['game_id'])
            res_a, res_b = int(request.form['res_a']), int(request.form['res_b'])
            g.score_a, g.score_b, g.status = res_a, res_b, 'encerrado'
            
            for b in g.bets:
                pts = calcular_pontos(b, res_a, res_b)
                b.points_earned = pts
                b.user.points_total += pts
        
        db.session.commit()
        flash('Operação realizada com sucesso!')
        return redirect(url_for('admin'))
        
    return render_template('admin.html', games=Game.query.all())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username'].lower()).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Usuário ou senha inválidos.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
