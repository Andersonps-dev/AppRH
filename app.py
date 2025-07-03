from flask import Flask, render_template, request, redirect, url_for, session, flash, g, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from models import User, Permission, Colaborador, Presenca, Empresa, Setor
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, date, timedelta
from functools import wraps
import logging
import io

from config import *

# Configuração de logs (opcional, descomente para depuração)
# logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

# Configurações do Flask
app.config['SECRET_KEY'] = 'admin_anderson_luft'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Sessão expira após 30 minutos
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Protege cookies contra acesso por JavaScript
app.config['SESSION_COOKIE_SECURE'] = True  # Requer HTTPS (desative em desenvolvimento local se não usar HTTPS)

db.init_app(app)
migrate = Migrate(app, db)

load_dotenv()

MASTER_USER = master_user
MASTER_PASS = master_pass

if not MASTER_USER or not MASTER_PASS:
    raise RuntimeError("MASTER_USER e MASTER_PASS precisam estar definidos no .env")

PERMISSIONS = [
    ('can_access_index', 'Acessa Início'),
    ('can_access_register_user', 'Acessa Cadastro Pessoa'),
    ('can_access_colaboradores', 'Acessa Colaboradores'),
    ('can_access_lista_presenca', 'Acessa Lista de Presença'),
    ('can_access_permissions', 'Acessa Permissões'),
]

# Adiciona cabeçalhos anti-cache
@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    # logging.debug(f"User ID na sessão: {user_id}")
    g.user = None
    if user_id is not None:
        g.user = User.query.get(user_id)
        # logging.debug(f"Usuário carregado: {g.user}")
    
    # Redireciona para login se não estiver logado e a rota não for pública
    public_routes = ['login', 'static', 'home']
    # logging.debug(f"Rota atual: {request.endpoint}")
    if not g.user and request.endpoint not in public_routes:
        # logging.debug("Redirecionando para login")
        flash('Faça login para acessar esta página.')
        return redirect(url_for('login', next=request.url))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            flash('Faça login para acessar esta página.')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def has_permission(user, perm_field):
    if not user:
        return False
    if user.username == MASTER_USER:
        return True
    perm = Permission.query.filter_by(role=user.role).first()
    return getattr(perm, perm_field, False) if perm else False

app.jinja_env.globals.update(has_permission=has_permission)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            if getattr(user, 'precisa_trocar_senha', False):
                return redirect(url_for('alterar_senha'))
            next_url = request.args.get('next') or url_for('index')
            return redirect(next_url)
        else:
            error = 'Usuário ou senha inválidos.'

    return render_template('login.html', error=error)

@app.route('/index')
@login_required
def index():
    if not has_permission(g.user, 'can_access_index'):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('login'))
    return render_template('index.html', user=g.user)

@app.route('/register_user', methods=['GET', 'POST'])
@login_required
def register_user():
    if not has_permission(g.user, 'can_access_register_user'):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('index'))
    if request.method == 'POST':
        nome_completo = request.form['nome_completo']
        username = request.form['username']
        role = request.form['role']
        setor_id = request.form['setor_id']
        empresa_ids = request.form.getlist('empresas')

        if User.query.filter_by(username=username).first():
            flash('Usuário já existe!')
        else:
            user = User(
                nome_completo=nome_completo,
                username=username,
                password=generate_password_hash('luft2025'),
                role=role,
                setor_id=setor_id,
                precisa_trocar_senha=True
            )
            user.empresas = Empresa.query.filter(Empresa.id.in_(empresa_ids)).all()
            db.session.add(user)
            db.session.commit()
            flash('Usuário cadastrado com sucesso! A senha inicial é "luft2025".')
        return redirect(url_for('register_user'))
    users = User.query.all()
    empresas = Empresa.query.order_by(Empresa.nome).all()
    setores = Setor.query.order_by(Setor.nome).all()
    return render_template('register_user.html', users=users, empresas=empresas, setores=setores, user=g.user)

@app.route('/logout')
def logout():
    session.clear()
    flash('Você foi desconectado.')
    return redirect(url_for('login'))

@app.route('/permissions', methods=['GET', 'POST'])
@login_required
def permissions():
    if not (g.user.username == MASTER_USER or has_permission(g.user, 'can_access_permissions')):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('index'))
    roles = ['master', 'admin', 'rh', 'coordenador', 'lider']
    if request.method == 'POST':
        for raw_role in roles:
            if raw_role == 'master':
                continue
            perm = Permission.query.filter_by(role=raw_role).first()
            if not perm:
                perm = Permission(role=raw_role)
                db.session.add(perm)
            for field, _ in PERMISSIONS:
                setattr(perm, field, bool(request.form.get(f'{raw_role}_{field}')))
        db.session.commit()
        flash('Permissões atualizadas!')
        return redirect(url_for('permissions'))
    permissions = {p.role: p for p in Permission.query.all()}
    return render_template(
        'permissions.html',
        user=g.user,
        permissions=permissions,
        roles=roles,
        PERMISSIONS=PERMISSIONS,
        getattr=getattr
    )

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not has_permission(g.user, 'can_access_register_user'):
        flash('Sem acesso.')
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    empresas = Empresa.query.order_by(Empresa.nome).all()
    setores = Setor.query.order_by(Setor.nome).all()
    if request.method == 'POST':
        user.nome_completo = request.form.get('nome_completo')
        user.username = request.form.get('username')
        password = request.form.get('password')
        if password:
            user.password = generate_password_hash(password)
        if user.username != 'luftsolutions.extrema':
            user.role = request.form.get('role')
        user.setor_id = request.form.get('setor_id')
        empresa_ids = request.form.getlist('empresas')
        user.empresas = Empresa.query.filter(Empresa.id.in_(empresa_ids)).all()
        db.session.commit()
        flash('Usuário atualizado com sucesso!')
        return redirect(url_for('register_user'))
    return render_template(
        'edit_user.html',
        edit_user=user,
        empresas=empresas,
        setores=setores
    )

@app.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if not has_permission(g.user, 'can_access_register_user'):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    if user.username == MASTER_USER:
        flash('Usuário master não pode ser excluído!')
        return redirect(url_for('register_user'))
    db.session.delete(user)
    db.session.commit()
    flash('Usuário excluído com sucesso!')
    return redirect(url_for('register_user'))

@app.route('/colaboradores', methods=['GET'])
@login_required
def colaboradores():
    if not has_permission(g.user, 'can_access_colaboradores'):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('index'))

    turnos = ['1º TURNO', '2º TURNO', 'COMERCIAL', '3º TURNO']
    status_list = ['ATIVO', 'INATIVO']

    filtro_nome = request.args.get('filtro_nome', '')
    filtro_empresa = request.args.get('filtro_empresa', '')
    filtro_status = request.args.get('filtro_status', '')
    filtro_setor = request.args.get('filtro_setor', '')
    filtro_gestor = request.args.get('filtro_gestor', '')

    query = Colaborador.query
    if filtro_nome:
        query = query.filter(Colaborador.nome.ilike(f'%{filtro_nome}%'))
    if filtro_empresa:
        query = query.filter(Colaborador.empresa_id == int(filtro_empresa))
    if filtro_status:
        query = query.filter(Colaborador.situacao.ilike(f'%{filtro_status}%'))
    if filtro_setor:
        query = query.filter(Colaborador.setor_id == int(filtro_setor))
    if filtro_gestor:
        query = query.filter(Colaborador.gestor.ilike(f'%{filtro_gestor}%'))
    colaboradores = query.all()

    empresas = Empresa.query.order_by(Empresa.nome).all()
    setores = Setor.query.order_by(Setor.nome).all()
    return render_template(
        'colaboradores.html',
        user=g.user,
        colaboradores=colaboradores,
        empresas=empresas,
        setores=setores,
        filtro_nome=filtro_nome,
        filtro_empresa=filtro_empresa,
        filtro_status=filtro_status,
        filtro_setor=filtro_setor,
        filtro_gestor=filtro_gestor
    )

@app.route('/export_colaboradores')
@login_required
def export_colaboradores():
    if not has_permission(g.user, 'can_access_colaboradores'):
        flash('Sem acesso.')
        return redirect(url_for('index'))
    filtro_nome = request.args.get('filtro_nome', '')
    filtro_empresa = request.args.get('filtro_empresa', '')
    filtro_status = request.args.get('filtro_status', '')
    filtro_setor = request.args.get('filtro_setor', '')
    filtro_gestor = request.args.get('filtro_gestor', '')

    query = Colaborador.query
    if filtro_nome:
        query = query.filter(Colaborador.nome.ilike(f'%{filtro_nome}%'))
    if filtro_empresa:
        query = query.filter(Colaborador.empresa_id == filtro_empresa)
    if filtro_status:
        query = query.filter(Colaborador.situacao.ilike(f'%{filtro_status}%'))
    if filtro_setor:
        query = query.filter(Colaborador.setor_id == int(filtro_setor))
    if filtro_gestor:
        query = query.filter(Colaborador.gestor.ilike(f'%{filtro_gestor}%'))
    colaboradores = query.all()

    data = []
    for c in colaboradores:
        data.append({
            'Nome': c.nome,
            'Cpf': c.cpf,
            'Função': c.funcao,
            'Admissão': c.admissao,
            'Setor': c.setor.nome if c.setor else '',
            'Turno': c.turno,
            'Empregador': c.empregador,
            'Situação': c.situacao,
            'Empresa': c.empresa.nome if c.empresa else '',
            'Gestor': c.gestor
        })
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name="colaboradores.xlsx", as_attachment=True)

@app.route('/upload_colaboradores', methods=['POST'])
@login_required
def upload_colaboradores():
    if not has_permission(g.user, 'can_access_colaboradores'):
        flash('Sem acesso.')
        return redirect(url_for('index'))
    file = request.files.get('file')
    if not file:
        flash('Nenhum arquivo enviado.')
        return redirect(url_for('colaboradores'))
    df = pd.read_excel(file)

    for idx, row in df.iterrows():
        cpf = row.get('Cpf')
        cpf = str(cpf).strip() if cpf and not pd.isna(cpf) else None
        if not cpf:
            continue

        admissao_val = row.get('Admissão')
        admissao = None
        if pd.isna(admissao_val) or admissao_val is None or str(admissao_val).strip() == '':
            continue
        try:
            if isinstance(admissao_val, (pd.Timestamp, datetime)):
                admissao = admissao_val.strftime('%Y-%m-%d')
            elif isinstance(admissao_val, float) or isinstance(admissao_val, int):
                admissao = pd.to_datetime(admissao_val, unit='d', origin='1899-12-30').strftime('%Y-%m-%d')
            else:
                admissao = pd.to_datetime(str(admissao_val), dayfirst=True, errors='coerce')
                if pd.isna(admissao):
                    raise ValueError
                admissao = admissao.strftime('%Y-%m-%d')
        except Exception:
            continue

        empresa_nome = row.get('Empresa')
        setor_nome = row.get('Setor')
        empresa = Empresa.query.filter_by(nome=empresa_nome).first() if empresa_nome else None
        setor = Setor.query.filter_by(nome=setor_nome).first() if setor_nome else None

        colaborador = Colaborador.query.filter_by(cpf=cpf).first()
        if colaborador:
            colaborador.nome = row.get('Nome')
            colaborador.funcao = row.get('Função')
            colaborador.admissao = admissao
            colaborador.setor_id = setor.id if setor else None
            colaborador.turno = row.get('Turno')
            colaborador.empregador = row.get('Empregador')
            colaborador.situacao = row.get('Situação')
            colaborador.empresa_id = empresa.id if empresa else None
            colaborador.gestor = row.get('Gestor')
        else:
            colaborador = Colaborador(
                nome=row.get('Nome'),
                cpf=cpf,
                funcao=row.get('Função'),
                admissao=admissao,
                setor_id=setor.id if setor else None,
                turno=row.get('Turno'),
                empregador=row.get('Empregador'),
                situacao=row.get('Situação'),
                empresa_id=empresa.id if empresa else None,
                gestor=row.get('Gestor')
            )
            db.session.add(colaborador)
    db.session.commit()
    flash('Colaboradores importados com sucesso!')
    return redirect(url_for('colaboradores'))

@app.route('/add_colaborador', methods=['POST'])
@login_required
def add_colaborador():
    if not has_permission(g.user, 'can_access_colaboradores'):
        flash('Sem acesso.')
        return redirect(url_for('index'))
    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    funcao = request.form.get('funcao')
    admissao = request.form.get('admissao')
    turno = request.form.get('turno')
    empregador = request.form.get('empregador')
    situacao = request.form.get('situacao')
    empresa_id = request.form.get('empresa_id')
    setor_id = request.form.get('setor_id')
    gestor = request.form.get('gestor')

    if not all([nome, cpf, funcao, admissao, turno, situacao, empresa_id, setor_id]):
        flash('Preencha todos os campos obrigatórios!')
        return redirect(url_for('colaboradores'))

    if Colaborador.query.filter_by(cpf=cpf).first():
        flash('Já existe um colaborador cadastrado com este CPF!')
        return redirect(url_for('colaboradores'))

    colaborador = Colaborador(
        nome=nome,
        cpf=cpf,
        funcao=funcao,
        admissao=admissao,
        setor_id=setor_id,
        turno=turno,
        empregador=empregador,
        situacao=situacao,
        empresa_id=empresa_id,
        gestor=gestor
    )
    db.session.add(colaborador)
    db.session.commit()
    flash('Colaborador cadastrado com sucesso!')
    return redirect(url_for('colaboradores'))

@app.route('/edit_colaborador/<int:colaborador_id>', methods=['GET', 'POST'])
@login_required
def edit_colaborador(colaborador_id):
    if not has_permission(g.user, 'can_access_colaboradores'):
        flash('Sem acesso.')
        return redirect(url_for('index'))
    colaborador = Colaborador.query.get_or_404(colaborador_id)
    if request.method == 'POST':
        colaborador.nome = request.form.get('nome')
        colaborador.cpf = request.form.get('cpf')
        colaborador.funcao = request.form.get('funcao')
        colaborador.admissao = request.form.get('admissao')
        colaborador.setor_id = request.form.get('setor_id')
        colaborador.turno = request.form.get('turno')
        colaborador.empregador = request.form.get('empregador')
        colaborador.situacao = request.form.get('situacao')
        colaborador.empresa_id = request.form.get('empresa_id')
        colaborador.gestor = request.form.get('gestor')
        db.session.commit()
        flash('Colaborador atualizado com sucesso!')
        return redirect(url_for('colaboradores'))
    empresas = Empresa.query.order_by(Empresa.nome).all()
    setores = Setor.query.order_by(Setor.nome).all()
    return render_template(
        'edit_colaborador.html',
        colaborador=colaborador,
        empresas=empresas,
        setores=setores,
        user=g.user
    )

@app.route('/delete_colaborador/<int:colaborador_id>')
@login_required
def delete_colaborador(colaborador_id):
    if not has_permission(g.user, 'can_access_colaboradores'):
        flash('Sem acesso.')
        return redirect(url_for('index'))
    colaborador = Colaborador.query.get_or_404(colaborador_id)
    db.session.delete(colaborador)
    db.session.commit()
    flash('Colaborador excluído com sucesso!')
    return redirect(url_for('colaboradores'))

@app.route('/lista_presenca', methods=['GET', 'POST'])
@login_required
def lista_presenca():
    if not has_permission(g.user, 'can_access_lista_presenca'):
        flash('Sem acesso.')
        return redirect(url_for('index'))

    user = g.user

    if request.method == 'POST':
        data_str = request.form.get('data')
        filtro_nome = request.form.get('filtro_nome', '')
        filtro_empresa = request.form.get('filtro_empresa', '')
        filtro_setor = request.form.get('filtro_setor', '')
        filtro_turno = request.form.get('filtro_turno', '')
        filtro_gestor = request.form.get('filtro_gestor', '')

        colaborador_ids = request.form.getlist('colaborador_ids')
        if colaborador_ids:
            colaboradores = Colaborador.query.filter(Colaborador.id.in_(colaborador_ids)).order_by(Colaborador.nome).all()
            for colaborador in colaboradores:
                status = request.form.get(f'status_{colaborador.id}', 'ausente')
                presenca = Presenca.query.filter_by(
                    colaborador_id=colaborador.id,
                    data=datetime.strptime(data_str, '%Y-%m-%d').date()
                ).first()
                if presenca:
                    presenca.status = status
                    presenca.usuario_id = user.id
                else:
                    presenca = Presenca(
                        colaborador_id=colaborador.id,
                        usuario_id=user.id,
                        data=datetime.strptime(data_str, '%Y-%m-%d').date(),
                        status=status
                    )
                    db.session.add(presenca)
            db.session.commit()
            flash('Lista de presença salva com sucesso!')
        else:
            flash('Nenhum colaborador filtrado para salvar!')
        return redirect(url_for('lista_presenca', data=data_str,
                                filtro_nome=filtro_nome,
                                filtro_empresa=filtro_empresa, filtro_setor=filtro_setor,
                                filtro_turno=filtro_turno, filtro_gestor=filtro_gestor))
    else:
        data_str = request.args.get('data')
        filtro_nome = request.args.get('filtro_nome', '')
        filtro_empresa = request.args.get('filtro_empresa', '')
        filtro_setor = request.args.get('filtro_setor', '')
        filtro_turno = request.args.get('filtro_turno', '')
        filtro_gestor = request.args.get('filtro_gestor', '')

    if data_str:
        try:
            data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
        except Exception:
            data_selecionada = date.today()
    else:
        data_selecionada = date.today()

    query = Colaborador.query
    if user.role in ['admin', 'master', 'rh']:
        pass
    elif user.role == 'coordenador':
        empresa_ids = [e.id for e in user.empresas]
        query = query.filter(Colaborador.empresa_id.in_(empresa_ids))
    else:
        query = query.filter(Colaborador.gestor == user.nome_completo)

    if filtro_nome:
        query = query.filter(Colaborador.nome.ilike(f'%{filtro_nome}%'))
    if filtro_empresa:
        query = query.filter(Colaborador.empresa_id == int(filtro_empresa))
    if filtro_setor:
        query = query.filter(Colaborador.setor_id == int(filtro_setor))
    if filtro_turno:
        query = query.filter(Colaborador.turno == filtro_turno)
    if filtro_gestor:
        query = query.filter(Colaborador.gestor.ilike(f'%{filtro_gestor}%'))

    colaboradores = query.order_by(Colaborador.nome).all()

    presencas = {p.colaborador_id: p for p in Presenca.query.filter(
        Presenca.data == data_selecionada,
        Presenca.colaborador_id.in_([c.id for c in colaboradores])
    ).all()}

    empresas = Empresa.query.order_by(Empresa.nome).all()
    setores = Setor.query.order_by(Setor.nome).all()
    turnos = ['1º TURNO', '2º TURNO', 'COMERCIAL', '3º TURNO']

    return render_template(
        'lista_presenca.html',
        user=user,
        colaboradores=colaboradores,
        presencas=presencas,
        data_selecionada=data_selecionada,
        empresas=empresas,
        setores=setores,
        turnos=turnos,
        filtro_nome=filtro_nome,
        filtro_empresa=filtro_empresa,
        filtro_setor=filtro_setor,
        filtro_turno=filtro_turno,
        filtro_gestor=filtro_gestor
    )

@app.route('/minhas_presencas', methods=['GET', 'POST'])
@login_required
def minhas_presencas():
    if g.user is None:
        flash('Faça login para acessar esta página.')
        return redirect(url_for('login'))

    user = g.user

    if request.method == 'POST':
        filtro_nome = request.form.get('filtro_nome', '')
        filtro_empresa = request.form.get('filtro_empresa', '')
        filtro_setor = request.form.get('filtro_setor', '')
        filtro_turno = request.form.get('filtro_turno', '')
        filtro_data = request.form.get('filtro_data', '')
        filtro_gestor = request.form.get('filtro_gestor', '')
    else:
        filtro_nome = request.args.get('filtro_nome', '')
        filtro_empresa = request.args.get('filtro_empresa', '')
        filtro_setor = request.args.get('filtro_setor', '')
        filtro_turno = request.args.get('filtro_turno', '')
        filtro_data = request.args.get('filtro_data', '')
        filtro_gestor = request.args.get('filtro_gestor', '')

    empresas = Empresa.query.order_by(Empresa.nome).all()
    setores = Setor.query.order_by(Setor.nome).all()

    query = Presenca.query.join(Colaborador)

    if user.role in ['admin', 'master', 'rh']:
        pass
    elif user.role == 'coordenador':
        empresa_ids = [e.id for e in user.empresas]
        query = query.filter(Colaborador.empresa_id.in_(empresa_ids))
    else:
        query = query.filter(Colaborador.gestor == user.nome_completo)

    if filtro_nome:
        query = query.filter(Colaborador.nome.ilike(f'%{filtro_nome}%'))
    if filtro_empresa:
        query = query.filter(Colaborador.empresa_id == int(filtro_empresa))
    if filtro_setor:
        query = query.filter(Colaborador.setor_id == int(filtro_setor))
    if filtro_turno:
        query = query.filter(Colaborador.turno == filtro_turno)
    if filtro_data:
        try:
            data_filtro = datetime.strptime(filtro_data, '%Y-%m-%d').date()
            query = query.filter(Presenca.data == data_filtro)
        except Exception:
            pass
    if filtro_gestor:
        query = query.filter(Colaborador.gestor.ilike(f'%{filtro_gestor}%'))

    presencas = query.order_by(Presenca.data.desc()).all()

    if request.method == 'POST':
        for p in presencas:
            novo_status = request.form.get(f'status_{p.id}')
            if novo_status and novo_status != p.status:
                p.status = novo_status
        db.session.commit()
        flash('Presenças atualizadas com sucesso!')
        return redirect(url_for('minhas_presencas',
                                filtro_nome=filtro_nome,
                                filtro_empresa=filtro_empresa,
                                filtro_setor=filtro_setor,
                                filtro_turno=filtro_turno,
                                filtro_data=filtro_data,
                                filtro_gestor=filtro_gestor))

    return render_template(
        'minhas_presencas.html',
        user=g.user,
        presencas=presencas,
        filtro_nome=filtro_nome,
        filtro_empresa=filtro_empresa,
        filtro_setor=filtro_setor,
        filtro_turno=filtro_turno,
        filtro_data=filtro_data,
        filtro_gestor=filtro_gestor,
        empresas=empresas,
        setores=setores
    )

@app.route('/delete_presenca/<int:presenca_id>', methods=['POST'])
@login_required
def delete_presenca(presenca_id):
    presenca = Presenca.query.get_or_404(presenca_id)
    db.session.delete(presenca)
    db.session.commit()
    flash('Presença excluída com sucesso!')
    return redirect(url_for('minhas_presencas'))

@app.route('/export_minhas_presencas')
@login_required
def export_minhas_presencas():
    if g.user is None:
        flash('Faça login para acessar esta página.')
        return redirect(url_for('login'))

    filtro_nome = request.args.get('filtro_nome', '')
    filtro_empresa = request.args.get('filtro_empresa', '')
    filtro_setor = request.args.get('filtro_setor', '')
    filtro_turno = request.args.get('filtro_turno', '')
    filtro_data = request.args.get('filtro_data', '')
    filtro_gestor = request.args.get('filtro_gestor', '')

    user = g.user

    query = Presenca.query.join(Colaborador)

    # Use a mesma lógica de permissão da tela de presenças
    if user.role in ['admin', 'master', 'rh']:
        pass
    elif user.role == 'coordenador':
        empresa_ids = [e.id for e in user.empresas]
        query = query.filter(Colaborador.empresa_id.in_(empresa_ids))
    else:
        query = query.filter(Colaborador.gestor == user.nome_completo)

    if filtro_nome:
        query = query.filter(Colaborador.nome.ilike(f'%{filtro_nome}%'))
    if filtro_empresa:
        query = query.filter(Colaborador.empresa_id == int(filtro_empresa))
    if filtro_setor:
        query = query.filter(Colaborador.setor_id == int(filtro_setor))
    if filtro_turno:
        query = query.filter(Colaborador.turno == filtro_turno)
    if filtro_data:
        try:
            data_filtro = datetime.strptime(filtro_data, '%Y-%m-%d').date()
            query = query.filter(Presenca.data == data_filtro)
        except Exception:
            pass
    if filtro_gestor:
        query = query.filter(Colaborador.gestor.ilike(f'%{filtro_gestor}%'))

    presencas = query.order_by(Presenca.data.desc()).all()

    data = []
    for p in presencas:
        data.append({
            'Data': p.data.strftime('%d/%m/%Y'),
            'Nome': p.colaborador.nome,
            'CPF': p.colaborador.cpf,
            'Setor': p.colaborador.setor.nome if p.colaborador.setor else '',
            'Turno': p.colaborador.turno,
            'Empresa': p.colaborador.empresa.nome if p.colaborador.empresa else '',
            'Gestor': p.colaborador.gestor,
            'Status': p.status
        })
    output = io.BytesIO()
    df = pd.DataFrame(data)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name="minhas_presencas.xlsx", as_attachment=True)

@app.route('/empresas', methods=['GET', 'POST'])
@login_required
def empresas():
    if g.user is None:
        flash('Faça login para acessar esta página.')
        return redirect(url_for('login'))
    if request.method == 'POST':
        nome = request.form.get('nome')
        if nome and not Empresa.query.filter_by(nome=nome).first():
            db.session.add(Empresa(nome=nome))
            db.session.commit()
            flash('Empresa cadastrada!')
        else:
            flash('Empresa já existe ou nome inválido!')
        return redirect(url_for('empresas'))
    empresas = Empresa.query.order_by(Empresa.nome).all()
    return render_template('empresas.html', empresas=empresas, user=g.user)

@app.route('/delete_empresa/<int:id>')
@login_required
def delete_empresa(id):
    empresa = Empresa.query.get_or_404(id)
    db.session.delete(empresa)
    db.session.commit()
    flash('Empresa excluída!')
    return redirect(url_for('empresas'))

@app.route('/setores', methods=['GET', 'POST'])
@login_required
def setores():
    if g.user is None:
        flash('Faça login para acessar esta página.')
        return redirect(url_for('login'))
    if request.method == 'POST':
        nome = request.form.get('nome')
        if nome and not Setor.query.filter_by(nome=nome).first():
            db.session.add(Setor(nome=nome))
            db.session.commit()
            flash('Setor cadastrado!')
        else:
            flash('Setor já existe ou nome inválido!')
        return redirect(url_for('setores'))
    setores = Setor.query.order_by(Setor.nome).all()
    return render_template('setores.html', setores=setores, user=g.user)

@app.route('/delete_setor/<int:id>')
@login_required
def delete_setor(id):
    setor = Setor.query.get_or_404(id)
    db.session.delete(setor)
    db.session.commit()
    flash('Setor excluído!')
    return redirect(url_for('setores'))

@app.route('/alterar_senha', methods=['GET', 'POST'])
@login_required
def alterar_senha():
    if g.user is None:
        flash('Faça login para acessar esta página.')
        return redirect(url_for('login'))
    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        if nova_senha != confirmar_senha:
            flash('A nova senha e a confirmação não conferem!')
        elif len(nova_senha) < 4:
            flash('A nova senha deve ter pelo menos 4 caracteres!')
        else:
            g.user.password = generate_password_hash(nova_senha)
            g.user.precisa_trocar_senha = False
            db.session.commit()
            flash('Senha alterada com sucesso!')
            return redirect(url_for('index'))
    return render_template('alterar_senha.html', user=g.user)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        empresa_luft = Empresa.query.filter_by(nome="LUFT").first()
        if not empresa_luft:
            empresa_luft = Empresa(nome="LUFT")
            db.session.add(empresa_luft)
            db.session.commit()
        setor_todos = Setor.query.filter_by(nome="TODOS").first()
        if not setor_todos:
            setor_todos = Setor(nome="TODOS")
            db.session.add(setor_todos)
            db.session.commit()
        master = User.query.filter_by(username=MASTER_USER).first()
        if not master:
            master = User(
                nome_completo="Master",
                username=MASTER_USER,
                password=generate_password_hash(MASTER_PASS),
                role='master',
                empresa_id=empresa_luft.id,
                setor_id=setor_todos.id
            )
            db.session.add(master)
            db.session.commit()
        else:
            updated = False
            if not check_password_hash(master.password, MASTER_PASS):
                master.password = generate_password_hash(MASTER_PASS)
                updated = True
            if master.role != 'master':
                master.role = 'master'
                updated = True
            if master.empresa_id != empresa_luft.id:
                master.empresa_id = empresa_luft.id
                updated = True
            if master.setor_id != setor_todos.id:
                master.setor_id = setor_todos.id
                updated = True
            if updated:
                db.session.commit()
    app.run(debug=True)