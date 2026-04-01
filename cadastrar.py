from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Cria as tabelas se não existirem
    db.create_all()
    
    # Dados do seu primeiro acesso
    usuario = "admin" 
    senha = "123" # Depois você pode mudar no código
    
    # Verifica se já existe para não duplicar
    if not User.query.filter_by(username=usuario).first():
        senha_hash = generate_password_hash(senha)
        novo_usuario = User(username=usuario, password=senha_hash)
        db.session.add(novo_usuario)
        db.session.commit()
        print(f"Usuario {usuario} criado com sucesso!")
    else:
        print("Usuario ja existe.")
