from database import db

user_empresas = db.Table(
    'user_empresas',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('empresa_id', db.Integer, db.ForeignKey('empresa.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_completo = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='lider')
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'))
    setor_id = db.Column(db.Integer, db.ForeignKey('setor.id'))
    empresas = db.relationship('Empresa', secondary=user_empresas, backref='usuarios')
    empresa = db.relationship('Empresa')
    setor = db.relationship('Setor')
    precisa_trocar_senha = db.Column(db.Boolean, default=True)

class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), unique=True, nullable=False)
    can_access_index = db.Column(db.Boolean, default=False)
    can_access_register_user = db.Column(db.Boolean, default=False)
    can_access_colaboradores = db.Column(db.Boolean, default=False)
    can_access_lista_presenca = db.Column(db.Boolean, default=False)
    can_access_permissions = db.Column(db.Boolean, default=False)

class Colaborador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    funcao = db.Column(db.String(100))
    admissao = db.Column(db.String(30), nullable=False)
    setor_id = db.Column(db.Integer, db.ForeignKey('setor.id'))
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'))
    turno = db.Column(db.String(30))
    empregador = db.Column(db.String(150))
    situacao = db.Column(db.String(50))
    gestor = db.Column(db.String(150))
    setor = db.relationship('Setor')
    empresa = db.relationship('Empresa')

class Presenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaborador.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='ausente')

    colaborador = db.relationship('Colaborador')
    usuario = db.relationship('User')

class Empresa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)

class Setor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)