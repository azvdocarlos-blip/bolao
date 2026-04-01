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
    score_a = db.Column(db.Integer, nullable=True)
    score_b = db.Column(db.Integer, nullable=True)
    date = db.Column(db.String(10), nullable=True)
    time = db.Column(db.String(5), nullable=True)
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
    b_a, b_b = int(bet.bet_score_a), int(bet.bet_score_b)
    r_a, r_b = int(real_a), int(real_b)
    if b_a == r_a and b_b == r_b: return 10
    if (r_a - r_b) == (b_a - b_b) and ((r_a > r_b and b_a > b_b) or (r_a < r_b and b_a < b_b)): return 7
    if (r_a > r_b and b_a > b_b) or (r_a < r_b and b_a < b_b) or (r_a == r_b and b_a == b_b): return 5
    return 0

# --- INICIALIZAÇÃO ---
with app.app_context():
    # Isso apaga e recria o banco se houver erro de coluna faltando
    db.create_all()
    usuarios = ['admin', 'edna', 'juliano', 'william', 'dorinha']
    for nome in usuarios:
        if not User.query.filter_by(username=nome).first():
            db.session.add(User(username=nome, password=generate_password_hash('123')))
    db.session.commit()

# --- ROTAS ---
@app.route('/')
@login_required
def index():
    games = Game.query.order_by(Game.date, Game.time).all()
    user_bets = {b.game_id: b for b in current_user.bets}
    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template('index.html', games=games, user_bets=user_bets, current_dt=now_dt)

@app.route('/ranking')
@login_required
def ranking():
    users = User.query.order_by(User.points_total.desc()).all()
    return render_template('ranking.html', users=users)

@app.route('/palpite/<int:game_id>', methods=['POST'])
@login_required
def palpite(game_id):
    game = Game.query.get_or_404(game_id)
    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M")
    if now_dt >= f"{game.date} {game.time}":
        flash('Palpites encerrados para este jogo!')
        return redirect(url_for('index'))
    
    b_a = request.form.get('score_a')
    b_b = request.form.get('score_b')
    bet = Bet.query.filter_by(user_id=current_user.id, game_id=game_id).first()
    if bet:
        bet.bet_score_a, bet.bet_score_b = b_a, b_b
    else:
        db.session.add(Bet(user_id=current_user.id, game_id=game_id, bet_score_a=b_a, bet_score_b=b_b))
    db.session.commit()
    flash('Palpite salvo!')
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if current_user.username != 'admin': return redirect(url_for('index'))
    if request.method == 'POST':
        if 'team_a' in request.form:
            db.session.add(Game(team_a=request.form['team_a'], team_b=request.form['team_b'], 
                                date=request.form['date'], time=request.form['time'], round_no=request.form['round_no']))
        elif 'game_id' in request.form:
            g = Game.query.get(request.form['game_id'])
            res_a, res_b = int(request.form['res_a']), int(request.form['res_b'])
            g.score_a, g.score_b, g.status = res_a, res_b, 'encerrado'
            for b in g.bets:
                pts = calcular_pontos(b, res_a, res_b)
                b.points_earned = pts
                b.user.points_total += pts
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('admin.html', games=Game.query.all())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            login_user(u); return redirect(url_for('index'))
        flash('Erro no login.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user(); return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
