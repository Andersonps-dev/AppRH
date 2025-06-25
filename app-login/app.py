from flask import Flask, render_template, request, redirect, url_for, session, flash, g, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Company, Permission, Empregador, Coordenador, Colaborador
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'admin_anderson_luft'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

load_dotenv()
# Ajuste para garantir que as variáveis estejam em maiúsculo
MASTER_USER = os.getenv('MASTER_USER') or os.getenv('master_user')
MASTER_PASS = os.getenv('MASTER_PASS') or os.getenv('master_pass')

if not MASTER_USER or not MASTER_PASS:
    raise RuntimeError("MASTER_USER e MASTER_PASS precisam estar definidos no .env")

PERMISSIONS = [
    ('can_access_index', 'Acessa Início'),
    ('can_access_register_person', 'Acessa Cadastro Pessoa'),
    ('can_access_register_company', 'Acessa Cadastro Empresa'),
    ('can_access_colaboradores', 'Acessa Colaboradores'),
    ('can_access_permissions', 'Acessa Permissões'),  # Adiciona permissão para tela de Permissões
    # Adicione novas permissões aqui, exemplo:
    # ('can_access_presenca', 'Acessa Presença'),
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
            session['company_id'] = company_id  # Salva empresa selecionada na sessão
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
        setor = request.form.get('setor')
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
                setor=None if all_setores else setor,
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

@app.route('/search')
def search():
    if g.user is None:
        return redirect(url_for('login'))
    query = request.args.get('q', '')
    # Aqui você pode adicionar lógica de busca
    return render_template('search_results.html', query=query, user=g.user)

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
    empregadores = Empregador.query.all()
    coordenadores = Coordenador.query.all()
    turnos = ['1º TURNO', '2º TURNO', 'COMERCIAL', '3º TURNO']
    status_list = ['Ativo', 'Inativo']

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
        query = query.filter(Colaborador.setor.ilike(f'%{filtro_setor}%'))
    if filtro_gestor:
        query = query.filter(Colaborador.gestor.ilike(f'%{filtro_gestor}%'))
    colaboradores = query.all()

    return render_template(
        'colaboradores.html',
        user=g.user,
        companies=companies,
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

    query = Colaborador.query
    if filtro_nome:
        query = query.filter(Colaborador.nome.ilike(f'%{filtro_nome}%'))
    if filtro_empresa:
        query = query.filter(Colaborador.empresa_id == filtro_empresa)
    if filtro_status:
        query = query.filter(Colaborador.status == filtro_status)
    colaboradores = query.all()

    data = []
    for c in colaboradores:
        data.append({
            'Nome': c.nome,
            'Departamento': c.departamento,
            'CPF': c.cpf,
            'Admissao': c.admissao.strftime('%d/%m/%Y') if c.admissao else '',
            'Função': c.funcao,
            'Empresa': c.empresa.name if c.empresa else '',
            # Adicione outros campos conforme necessário
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
    erros = []
    for idx, row in df.iterrows():
        empresa_nome = row.get('Empresa')
        empresa = Company.query.filter_by(name=empresa_nome).first() if empresa_nome else None
        if empresa_nome and not empresa:
            erros.append(f"Linha {idx+2}: Empresa '{empresa_nome}' não encontrada.")
            continue

        cpf = str(row.get('Cpf')).strip() if row.get('Cpf') else None
        if not cpf:
            erros.append(f"Linha {idx+2}: CPF não preenchido.")
            continue

        admissao_val = row.get('Admissão')
        admissao = None
        if pd.isna(admissao_val) or admissao_val is None or str(admissao_val).strip() == '':
            erros.append(f"Linha {idx+2}: Data de admissão não preenchida.")
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
            erros.append(f"Linha {idx+2}: Data de admissão inválida.")
            continue

        colaborador = Colaborador.query.filter_by(cpf=cpf).first()
        if colaborador:
            colaborador.nome = row.get('Nome')
            colaborador.funcao = row.get('Função')
            colaborador.admissao = admissao
            colaborador.setor = row.get('Setor')
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
                setor=row.get('Setor'),
                turno=row.get('Turno'),
                empregador=row.get('Empregador'),
                situacao=row.get('Situação'),
                empresa_id=empresa.id if empresa else None,
                gestor=row.get('Gestor')
            )
            db.session.add(colaborador)
    db.session.commit()
    if erros:
        flash('Alguns colaboradores não foram importados:<br>' + '<br>'.join(erros))
    else:
        flash('Colaboradores importados com sucesso!')
    return redirect(url_for('colaboradores'))

# Exemplo de rota para adicionar colaborador manualmente
@app.route('/add_colaborador', methods=['POST'])
def add_colaborador():
    if g.user is None or not has_permission(g.user, 'can_access_colaboradores'):
        flash('Sem acesso.')
        return redirect(url_for('index'))
    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    funcao = request.form.get('funcao')
    admissao = request.form.get('admissao')
    setor = request.form.get('setor')
    turno = request.form.get('turno')
    empregador = request.form.get('empregador')
    situacao = request.form.get('situacao')
    empresa_id = request.form.get('empresa_id')
    gestor = request.form.get('gestor')

    colaborador = Colaborador(
        nome=nome,
        cpf=cpf,
        funcao=funcao,
        admissao=admissao,
        setor=setor,
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Cria empresa "Luft" se não existir
        if not Company.query.filter_by(name='LUFT').first():
            db.session.add(Company(name='LUFT'))
            db.session.commit()
        # Cria ou atualiza o usuário master
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