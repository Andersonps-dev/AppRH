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
    departamento = db.Column(db.String(100))
    cpf = db.Column(db.String(20))
    admissao = db.Column(db.Date, nullable=False)
    funcao = db.Column(db.String(100))
    area = db.Column(db.String(100))
    setor = db.Column(db.String(100))
    empregador_id = db.Column(db.Integer, db.ForeignKey('empregador.id'), nullable=True)
    empregador = db.relationship('Empregador')
    turno = db.Column(db.String(30))
    situacao = db.Column(db.String(50))
    base_site = db.Column(db.String(100))
    coordenador_id = db.Column(db.Integer, db.ForeignKey('coordenador.id'), nullable=True)
    coordenador = db.relationship('Coordenador')
    gerente = db.Column(db.String(100))
    status = db.Column(db.String(20))
    tipo = db.Column(db.String(50))
    fretado = db.Column(db.String(50))
    armario = db.Column(db.String(50))
    telefone = db.Column(db.String(50))
    genero = db.Column(db.String(20))
    rg = db.Column(db.String(30))
    data_emissao = db.Column(db.Date)
    pis = db.Column(db.String(30))
    nome_pai = db.Column(db.String(100))
    nome_mae = db.Column(db.String(100))
    nascimento = db.Column(db.Date)
    endereco = db.Column(db.String(200))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    uf = db.Column(db.String(2))
    cep = db.Column(db.String(20))
    demissao = db.Column(db.Date)
    empresa_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    empresa = db.relationship('Company')