from flask import Flask, render_template, request, redirect, url_for, session, flash, g, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Company, Permission, Colaborador, Presenca, Setor  # Adicione Setor aqui
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, date
import io

app = Flask(__name__)

app.config['SECRET_KEY'] = 'admin_anderson_luft'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

load_dotenv()
MASTER_USER = "luftsolutions.extrema"
MASTER_PASS = "luftsolutions.extrema"

if not MASTER_USER or not MASTER_PASS:
    raise RuntimeError("MASTER_USER e MASTER_PASS precisam estar definidos no .env")

PERMISSIONS = [
    ('can_access_index', 'Acessa Início'),
    ('can_access_register_person', 'Acessa Cadastro Pessoa'),
    ('can_access_register_company', 'Acessa Cadastro Empresa'),
    ('can_access_colaboradores', 'Acessa Colaboradores'),
    ('can_access_lista_presenca', 'Acessa Lista de Presença'),
    ('can_access_register_sector', 'Acessa Cadastro Setor'),
    ('can_access_permissions', 'Acessa Permissões'),
]

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    companies = Company.query.all()
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        company_id = request.form['company']

        # Busca usuário que pode acessar todas as empresas OU usuário da empresa selecionada
        user = User.query.filter_by(username=username).filter(
            (User.company_id == company_id) | (User.all_companies == True)
        ).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['company_id'] = company_id
            return redirect(url_for('index'))
        else:
            error = 'Usuário, senha ou empresa inválidos.'

    return render_template('login.html', companies=companies, error=error)

@app.route('/index')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not has_permission(user, 'can_access_index'):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('login'))
    return render_template('index.html', user=user)

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = None
    if user_id is not None:
        g.user = User.query.get(user_id)

def has_permission(user, perm_field):
    if user.role == 'master' or user.username == MASTER_USER:
        return True
    perm = Permission.query.filter_by(role=user.role).first()
    return getattr(perm, perm_field, False) if perm else False

app.jinja_env.globals.update(has_permission=has_permission)

@app.route('/register_person', methods=['GET', 'POST'])
def register_person():
    if g.user is None:
        return redirect(url_for('login'))
    if not has_permission(g.user, 'can_access_register_person'):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('index'))
    companies = Company.query.all()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        company_id = request.form.get('company')
        all_companies = bool(request.form.get('all_companies'))
        role = request.form.get('role')
        setor_nome = request.form.get('setor')
        turno = request.form.get('turno')
        all_setores = bool(request.form.get('all_setores'))  # <-- Defina aqui!
        all_turnos = bool(request.form.get('all_turnos'))    # <-- Defina aqui!

        setor_obj = None
        if setor_nome and not all_setores:
            setor_obj = Setor.query.filter_by(nome=setor_nome.strip()).first()
            if not setor_obj:
                setor_obj = Setor(nome=setor_nome.strip())
                db.session.add(setor_obj)
                db.session.commit()
        turno = request.form.get('turno')
        all_setores = bool(request.form.get('all_setores'))
        all_turnos = bool(request.form.get('all_turnos'))
        if role == 'admin' and g.user.role != 'master':
            flash('Apenas o usuário master pode criar admins!')
            return redirect(url_for('register_person'))
        if all_companies:
            company_id = None
        if User.query.filter_by(username=username).first():
            flash('Usuário já existe!')
        else:
            user = User(
                username=username,
                password=generate_password_hash(password),
                company_id=company_id,
                all_companies=all_companies,
                role=role,
                setor=None if all_setores else setor_obj,  # Agora é objeto Setor!
                turno=None if all_turnos else turno,
                all_setores=all_setores,
                all_turnos=all_turnos
            )
            db.session.add(user)
            db.session.commit()
            flash('Usuário cadastrado com sucesso!')
        return redirect(url_for('register_person'))
    users = User.query.all()
    return render_template('register_person.html', user=g.user, companies=companies, users=users)

@app.route('/register_company', methods=['GET', 'POST'])
def register_company():
    if g.user is None:
        return redirect(url_for('login'))
    if not has_permission(g.user, 'can_access_register_company'):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form['empresa']
        if Company.query.filter_by(name=name).first():
            flash('Empresa já existe!')
        else:
            company = Company(name=name)
            db.session.add(company)
            db.session.commit()
            flash('Empresa cadastrada com sucesso!')
        return redirect(url_for('register_company'))
    companies = Company.query.all()
    return render_template('register_company.html', user=g.user, companies=companies)

@app.route('/edit_company/<int:company_id>', methods=['GET', 'POST'])
def edit_company(company_id):
    if g.user is None:
        return redirect(url_for('login'))
    if not has_permission(g.user, 'can_access_register_company'):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('index'))
    company = Company.query.get_or_404(company_id)
    if request.method == 'POST':
        company.name = request.form['empresa']
        db.session.commit()
        flash('Empresa atualizada com sucesso!')
        return redirect(url_for('register_company'))
    return render_template('edit_company.html', user=g.user, edit_company=company)

@app.route('/delete_company/<int:company_id>')
def delete_company(company_id):
    if g.user is None:
        return redirect(url_for('login'))
    if not has_permission(g.user, 'can_access_register_company'):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('index'))
    company = Company.query.get_or_404(company_id)
    db.session.delete(company)
    db.session.commit()
    flash('Empresa excluída com sucesso!')
    return redirect(url_for('register_company'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/permissions', methods=['GET', 'POST'])
def permissions():
    if g.user is None or not (g.user.role == 'master' or g.user.username == MASTER_USER or has_permission(g.user, 'can_access_permissions')):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('index'))
    roles = ['master', 'admin', 'rh', 'coordenador', 'lider']
    if request.method == 'POST':
        for role in roles:
            if role == 'master':
                continue
            perm = Permission.query.filter_by(role=role).first()
            if not perm:
                perm = Permission(role=role)
                db.session.add(perm)
            for field, _ in PERMISSIONS:
                setattr(perm, field, bool(request.form.get(f'{role}_{field}')))
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
        getattr=getattr  # <-- Adicione isso!
    )

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if g.user is None or not has_permission(g.user, 'can_access_register_person'):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    companies = Company.query.all()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form.get('password')
        company_id = request.form.get('company')
        all_companies = bool(request.form.get('all_companies'))
        role = request.form.get('role')
        if password:
            user.password = generate_password_hash(password)
        user.username = username
        user.company_id = company_id if not all_companies else None
        user.all_companies = all_companies
        user.role = role
        db.session.commit()
        flash('Usuário atualizado com sucesso!')
        return redirect(url_for('register_person'))
    return render_template('edit_user.html', user=g.user, edit_user=user, companies=companies)

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    if g.user is None or not has_permission(g.user, 'can_access_register_person'):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    if user.username == MASTER_USER:
        flash('Usuário master não pode ser excluído!')
        return redirect(url_for('register_person'))
    db.session.delete(user)
    db.session.commit()
    flash('Usuário excluído com sucesso!')
    return redirect(url_for('register_person'))

@app.route('/colaboradores', methods=['GET'])
def colaboradores():
    if g.user is None:
        return redirect(url_for('login'))
    if not has_permission(g.user, 'can_access_colaboradores'):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('index'))

    companies = Company.query.all()
    setores = Setor.query.order_by(Setor.nome).all()  # Adicione esta linha
    turnos = ['1º TURNO', '2º TURNO', 'COMERCIAL', '3º TURNO']
    status_list = ['ATIVO', 'INATIVO']

    # Filtros
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

    return render_template(
        'colaboradores.html',
        user=g.user,
        companies=companies,
        setores=setores,  # <-- Passe para o template
        colaboradores=colaboradores,
        turnos=turnos,
        status_list=status_list,
        filtro_nome=filtro_nome,
        filtro_empresa=filtro_empresa,
        filtro_status=filtro_status,
        filtro_setor=filtro_setor,
        filtro_gestor=filtro_gestor,
        estados=[{'sigla': 'MG', 'nome': 'Minas Gerais'}, {'sigla': 'SP', 'nome': 'São Paulo'}]  # Exemplo, ajuste conforme necessário
    )

@app.route('/export_colaboradores')
def export_colaboradores():
    if g.user is None or not has_permission(g.user, 'can_access_colaboradores'):
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
        # Se filtro_setor for o id do setor:
        query = query.filter(Colaborador.setor_id == int(filtro_setor))
        # Se for o nome do setor, use:
        # query = query.join(Setor).filter(Setor.nome.ilike(f'%{filtro_setor}%'))
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
            'Empresa': c.empresa.name if c.empresa else '',
            'Gestor': c.gestor
        })
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name="colaboradores.xlsx", as_attachment=True)

# Exemplo de rota para importar colaboradores via Excel
@app.route('/upload_colaboradores', methods=['POST'])
def upload_colaboradores():
    if g.user is None or not has_permission(g.user, 'can_access_colaboradores'):
        flash('Sem acesso.')
        return redirect(url_for('index'))
    file = request.files.get('file')
    if not file:
        flash('Nenhum arquivo enviado.')
        return redirect(url_for('colaboradores'))
    df = pd.read_excel(file)
    empresas_nao_cadastradas = set()
    setores_nao_cadastrados = set()
    for idx, row in df.iterrows():
        empresa_nome = row.get('Empresa')
        empresa = Company.query.filter_by(name=empresa_nome).first() if empresa_nome else None
        if empresa_nome and not empresa:
            empresas_nao_cadastradas.add(empresa_nome)
            continue

        cpf = str(row.get('Cpf')).strip() if row.get('Cpf') else None
        if not cpf:
            continue

        admissao_val = row.get('Admissão')
        admissao = None
        if pd.isna(admissao_val) or admissao_val is None or str(admissao_val).strip() == '':
            continue
        try:
            if isinstance(admissao_val, (pd.Timestamp, datetime)):
                admissao = admissao_val.strftime('%d/%m/%Y')
            elif isinstance(admissao_val, float) or isinstance(admissao_val, int):
                admissao = pd.to_datetime(admissao_val, unit='d', origin='1899-12-30').strftime('%d/%m/%Y')
            else:
                admissao = pd.to_datetime(str(admissao_val), dayfirst=True, errors='coerce')
                if pd.isna(admissao):
                    raise ValueError
                admissao = admissao.strftime('%d/%m/%Y')
        except Exception:
            continue

        setor_nome = row.get('Setor')
        setor_obj = None
        if setor_nome and str(setor_nome).strip():
            setor_obj = Setor.query.filter_by(nome=str(setor_nome).strip()).first()
            if not setor_obj:
                setores_nao_cadastrados.add(str(setor_nome).strip())
                continue  # pula este colaborador

        colaborador = Colaborador.query.filter_by(cpf=cpf).first()
        if colaborador:
            colaborador.nome = row.get('Nome')
            colaborador.funcao = row.get('Função')
            colaborador.admissao = admissao
            colaborador.setor = setor_obj
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
                setor=setor_obj,
                turno=row.get('Turno'),
                empregador=row.get('Empregador'),
                situacao=row.get('Situação'),
                empresa_id=empresa.id if empresa else None,
                gestor=row.get('Gestor')
            )
            db.session.add(colaborador)
    db.session.commit()
    mensagens = []
    if empresas_nao_cadastradas:
        empresas_str = ', '.join(sorted(empresas_nao_cadastradas))
        mensagens.append(f'Falta cadastrar as seguintes empresas antes de importar: {empresas_str}')
    if setores_nao_cadastrados:
        setores_str = ', '.join(sorted(setores_nao_cadastrados))
        mensagens.append(f'Falta cadastrar os seguintes setores antes de importar: {setores_str}')
    if not mensagens:
        mensagens.append('Colaboradores importados com sucesso!')
    for msg in mensagens:
        flash(msg)
    return redirect(url_for('colaboradores'))

@app.route('/add_colaborador', methods=['POST'])
def add_colaborador():
    if g.user is None or not has_permission(g.user, 'can_access_colaboradores'):
        flash('Sem acesso.')
        return redirect(url_for('index'))
    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    funcao = request.form.get('funcao')  # Certo!
    admissao = request.form.get('admissao')  # Certo!
    setor_id = request.form.get('setor_id')
    setor_obj = Setor.query.get(setor_id) if setor_id else None
    turno = request.form.get('turno')
    empregador = request.form.get('empregador')
    situacao = request.form.get('situacao')
    empresa_id = request.form.get('empresa_id')  # Certo!
    gestor = request.form.get('gestor')

    # Validação extra (opcional)
    if not all([nome, cpf, funcao, admissao, setor_obj, turno, situacao, empresa_id]):
        flash('Preencha todos os campos obrigatórios!')
        return redirect(url_for('colaboradores'))

    colaborador = Colaborador(
        nome=nome,
        cpf=cpf,
        funcao=funcao,
        admissao=admissao,
        setor=setor_obj,
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
def edit_colaborador(colaborador_id):
    if g.user is None or not has_permission(g.user, 'can_access_colaboradores'):
        flash('Sem acesso.')
        return redirect(url_for('index'))
    colaborador = Colaborador.query.get_or_404(colaborador_id)
    companies = Company.query.all()
    if request.method == 'POST':
        colaborador.nome = request.form.get('nome')
        colaborador.cpf = request.form.get('cpf')
        colaborador.funcao = request.form.get('funcao')
        colaborador.admissao = request.form.get('admissao')
        colaborador.setor = request.form.get('setor')
        colaborador.turno = request.form.get('turno')
        colaborador.empregador = request.form.get('empregador')
        colaborador.situacao = request.form.get('situacao')
        colaborador.empresa_id = request.form.get('empresa_id')
        colaborador.gestor = request.form.get('gestor')
        db.session.commit()
        flash('Colaborador atualizado com sucesso!')
        return redirect(url_for('colaboradores'))
    return render_template('edit_colaborador.html', user=g.user, colaborador=colaborador, companies=companies)

@app.route('/delete_colaborador/<int:colaborador_id>')
def delete_colaborador(colaborador_id):
    if g.user is None or not has_permission(g.user, 'can_access_colaboradores'):
        flash('Sem acesso.')
        return redirect(url_for('index'))
    colaborador = Colaborador.query.get_or_404(colaborador_id)
    db.session.delete(colaborador)
    db.session.commit()
    flash('Colaborador excluído com sucesso!')
    return redirect(url_for('colaboradores'))

@app.route('/lista_presenca', methods=['GET', 'POST'])
def lista_presenca():
    if g.user is None:
        return redirect(url_for('login'))
    if not has_permission(g.user, 'can_access_lista_presenca'):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('index'))

    # Filtros do usuário logado
    user = g.user
    empresa_id = user.company_id if not user.all_companies else None
    setor = user.setor if not user.all_setores else None
    turno = user.turno if not user.all_turnos else None

    # Data selecionada
    data_str = request.form.get('data') if request.method == 'POST' else request.args.get('data')
    if data_str:
        try:
            data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
        except Exception:
            data_selecionada = date.today()
    else:
        data_selecionada = date.today()

    # Busca colaboradores conforme permissão do usuário
    query = Colaborador.query
    if empresa_id:
        query = query.filter(Colaborador.empresa_id == empresa_id)
    if setor:
        query = query.filter(Colaborador.setor == setor)
    if turno:
        query = query.filter(Colaborador.turno == turno)
    colaboradores = query.order_by(Colaborador.nome).all()

    # Salvar presença
    if request.method == 'POST':
        for colaborador in colaboradores:
            status = request.form.get(f'status_{colaborador.id}', 'ausente')
            presenca = Presenca.query.filter_by(
                colaborador_id=colaborador.id,
                data=data_selecionada
            ).first()
            if presenca:
                presenca.status = status
                presenca.usuario_id = user.id
            else:
                presenca = Presenca(
                    colaborador_id=colaborador.id,
                    usuario_id=user.id,
                    data=data_selecionada,
                    status=status
                )
                db.session.add(presenca)
        db.session.commit()
        flash('Lista de presença salva com sucesso!')
        return redirect(url_for('lista_presenca', data=data_selecionada.strftime('%Y-%m-%d')))

    # Buscar presenças já salvas para a data
    presencas = {p.colaborador_id: p for p in Presenca.query.filter(
        Presenca.data == data_selecionada,
        Presenca.colaborador_id.in_([c.id for c in colaboradores])
    ).all()}

    return render_template(
        'lista_presenca.html',
        user=user,
        colaboradores=colaboradores,
        presencas=presencas,
        data_selecionada=data_selecionada
    )

@app.route('/minhas_presencas', methods=['GET', 'POST'])
def minhas_presencas():
    if g.user is None:
        return redirect(url_for('login'))

    filtro_nome = request.args.get('filtro_nome', '')
    filtro_empresa = request.args.get('filtro_empresa', '')
    filtro_setor = request.args.get('filtro_setor', '')
    filtro_turno = request.args.get('filtro_turno', '')
    filtro_data = request.args.get('filtro_data', '')

    empresas = Company.query.all()
    setores = Setor.query.all()

    # Busca presenças baseadas nos filtros do usuário, não só pelo usuario_id
    query = Presenca.query.join(Colaborador)

    # Filtros do usuário logado
    if not g.user.all_companies and g.user.company_id:
        query = query.filter(Colaborador.empresa_id == g.user.company_id)
    if not g.user.all_setores and g.user.setor_id:
        query = query.filter(Colaborador.setor_id == g.user.setor_id)
    if not g.user.all_turnos and g.user.turno:
        query = query.filter(Colaborador.turno == g.user.turno)

    # Filtros da tela
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

    presencas = query.order_by(Presenca.data.desc()).all()

    # Atualização dos status
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
            filtro_data=filtro_data
        ))

    return render_template(
        'minhas_presencas.html',
        user=g.user,
        presencas=presencas,
        empresas=empresas,
        setores=setores,
        filtro_nome=filtro_nome,
        filtro_empresa=filtro_empresa,
        filtro_setor=filtro_setor,
        filtro_turno=filtro_turno,
        filtro_data=filtro_data
    )

@app.route('/register_sector', methods=['GET', 'POST'])
def register_sector():
    if g.user is None:
        return redirect(url_for('login'))
    if not has_permission(g.user, 'can_access_register_sector'):
        flash('Sem acesso. Entre em contato: analiseoperacional.extrema@luftsolutions.com.br')
        return redirect(url_for('index'))
    if request.method == 'POST':
        nome = request.form['setor']
        if Setor.query.filter_by(nome=nome).first():
            flash('Setor já existe!')
        else:
            setor = Setor(nome=nome)
            db.session.add(setor)
            db.session.commit()
            flash('Setor cadastrado com sucesso!')
        return redirect(url_for('register_sector'))
    setores = Setor.query.all()
    return render_template('register_sector.html', user=g.user, setores=setores)

@app.route('/edit_sector/<int:setor_id>', methods=['GET', 'POST'])
def edit_sector(setor_id):
    setor = Setor.query.get_or_404(setor_id)
    if request.method == 'POST':
        nome = request.form['setor']
        if Setor.query.filter(Setor.nome == nome, Setor.id != setor_id).first():
            flash('Já existe um setor com esse nome!')
        else:
            setor.nome = nome
            db.session.commit()
            flash('Setor atualizado com sucesso!')
            return redirect(url_for('register_sector'))
    return render_template('edit_sector.html', user=g.user, setor=setor)

@app.route('/delete_sector/<int:setor_id>', methods=['POST'])
def delete_sector(setor_id):
    setor = Setor.query.get_or_404(setor_id)
    db.session.delete(setor)
    db.session.commit()
    flash('Setor excluído com sucesso!')
    return redirect(url_for('register_sector'))

@app.route('/delete_presenca/<int:presenca_id>', methods=['POST'])
def delete_presenca(presenca_id):
    presenca = Presenca.query.get_or_404(presenca_id)
    if presenca.usuario_id != g.user.id and g.user.role not in ['admin', 'master']:
        flash('Sem permissão para excluir esta presença.')
        return redirect(url_for('minhas_presencas'))
    db.session.delete(presenca)
    db.session.commit()
    flash('Presença excluída com sucesso!')
    return redirect(url_for('minhas_presencas'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Company.query.filter_by(name='LUFT').first():
            db.session.add(Company(name='LUFT'))
            db.session.commit()
        master = User.query.filter_by(username=MASTER_USER).first()
        if not master:
            master = User(
                username=MASTER_USER,
                password=generate_password_hash(MASTER_PASS),
                role='master',
                all_companies=True
            )
            db.session.add(master)
            db.session.commit()
        else:
            master.role = 'master'
            master.all_companies = True
            if not check_password_hash(master.password, MASTER_PASS):
                master.password = generate_password_hash(MASTER_PASS)
            db.session.commit()
    app.run(debug=True)