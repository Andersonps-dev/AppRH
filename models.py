from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    users = db.relationship('User', backref='company', lazy=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    role = db.Column(db.String(50), nullable=False, default='user')  # admin, rh, coordenador, lider
    all_companies = db.Column(db.Boolean, default=False)

class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), nullable=False, unique=True)
    can_access_index = db.Column(db.Boolean, default=True)
    can_access_register_person = db.Column(db.Boolean, default=False)
    can_access_register_company = db.Column(db.Boolean, default=False)
    can_access_colaboradores = db.Column(db.Boolean, default=False)
    # Para nova tela:
    # can_access_presenca = db.Column(db.Boolean, default=False)

class Empregador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), unique=True, nullable=False)

class Coordenador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), unique=True, nullable=False)

class Colaborador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    empresa = db.relationship('Company')
    admissao = db.Column(db.Date, nullable=False)
    demissao = db.Column(db.Date, nullable=True)
    empregador_id = db.Column(db.Integer, db.ForeignKey('empregador.id'), nullable=False)
    empregador = db.relationship('Empregador')
    turno = db.Column(db.String(30), nullable=False)
    coordenador_id = db.Column(db.Integer, db.ForeignKey('coordenador.id'), nullable=False)
    coordenador = db.relationship('Coordenador')
    status = db.Column(db.String(20), nullable=False)  # Ativo, Inativo