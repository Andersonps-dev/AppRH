from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Company, Permission, Empregador, Coordenador, Colaborador
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'admin_anderson_luft'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

load_dotenv()
MASTER_USER = os.getenv('MASTER_USER')
MASTER_PASS = os.getenv('MASTER_PASS')

PERMISSIONS = [
    ('can_access_index', 'Acessa Início'),
    ('can_access_register_person', 'Acessa Cadastro Pessoa'),
    ('can_access_register_company', 'Acessa Cadastro Empresa'),
    ('can_access_colaboradores', 'Acessa Colaboradores'),
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
                role=role
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
    if g.user is None or (g.user.role != 'admin' and g.user.role != 'master'):
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
    return render_template('permissions.html', user=g.user, permissions=permissions, roles=roles, PERMISSIONS=PERMISSIONS)

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

@app.route('/colaboradores', methods=['GET', 'POST'])
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

    if request.method == 'POST':
        nome = request.form['nome']
        empresa_id = request.form['empresa']
        admissao = datetime.strptime(request.form['admissao'], '%Y-%m-%d')
        demissao = request.form['demissao']
        demissao = datetime.strptime(demissao, '%Y-%m-%d') if demissao else None
        empregador_id = request.form['empregador']
        turno = request.form['turno']
        coordenador_id = request.form['coordenador']
        status = request.form['status']
        colaborador = Colaborador(
            nome=nome,
            empresa_id=empresa_id,
            admissao=admissao,
            demissao=demissao,
            empregador_id=empregador_id,
            turno=turno,
            coordenador_id=coordenador_id,
            status=status
        )
        db.session.add(colaborador)
        db.session.commit()
        flash('Colaborador cadastrado com sucesso!')
        return redirect(url_for('colaboradores'))

    colaboradores = Colaborador.query.all()
    return render_template('colaboradores.html', user=g.user, companies=companies, empregadores=empregadores,
                           coordenadores=coordenadores, turnos=turnos, status_list=status_list, colaboradores=colaboradores)

@app.route('/colaboradores/upload', methods=['POST'])
def upload_colaboradores():
    if g.user is None:
        return redirect(url_for('login'))
    file = request.files['file']
    if not file:
        flash('Nenhum arquivo enviado!')
        return redirect(url_for('colaboradores'))
    df = pd.read_excel(file)
    for _, row in df.iterrows():
        empresa = Company.query.filter_by(name=row['EMPRESA']).first()
        empregador = Empregador.query.filter_by(nome=row['EMPREGADOR']).first()
        coordenador = Coordenador.query.filter_by(nome=row['COORDENADOR']).first()
        if not empresa or not empregador or not coordenador:
            continue  # Pula se não encontrar referência
        admissao = pd.to_datetime(row['ADMISSÃO']).date()
        demissao = pd.to_datetime(row['DEMISSÃO']).date() if pd.notnull(row['DEMISSÃO']) else None
        colaborador = Colaborador(
            nome=row['NOME'],
            empresa_id=empresa.id,
            admissao=admissao,
            demissao=demissao,
            empregador_id=empregador.id,
            turno=row['TURNO'],
            coordenador_id=coordenador.id,
            status=row['STATUS']
        )
        db.session.add(colaborador)
    db.session.commit()
    flash('Colaboradores importados com sucesso!')
    return redirect(url_for('colaboradores'))

@app.route('/empregadores', methods=['GET', 'POST'])
def empregadores():
    if g.user is None:
        return redirect(url_for('login'))
    if request.method == 'POST':
        nome = request.form['nome']
        if not Empregador.query.filter_by(nome=nome).first():
            db.session.add(Empregador(nome=nome))
            db.session.commit()
            flash('Empregador cadastrado!')
        return redirect(url_for('empregadores'))
    empregadores = Empregador.query.all()
    return render_template('empregadores.html', user=g.user, empregadores=empregadores)

@app.route('/coordenadores', methods=['GET', 'POST'])
def coordenadores():
    if g.user is None:
        return redirect(url_for('login'))
    if request.method == 'POST':
        nome = request.form['nome']
        if not Coordenador.query.filter_by(nome=nome).first():
            db.session.add(Coordenador(nome=nome))
            db.session.commit()
            flash('Coordenador cadastrado!')
        return redirect(url_for('coordenadores'))
    coordenadores = Coordenador.query.all()
    return render_template('coordenadores.html', user=g.user, coordenadores=coordenadores)

@app.route('/colaboradores/edit/<int:id>', methods=['GET', 'POST'])
def edit_colaborador(id):
    if g.user is None:
        return redirect(url_for('login'))
    colaborador = Colaborador.query.get_or_404(id)
    companies = Company.query.all()
    empregadores = Empregador.query.all()
    coordenadores = Coordenador.query.all()
    turnos = ['1º TURNO', '2º TURNO', 'COMERCIAL', '3º TURNO']
    status_list = ['Ativo', 'Inativo']
    if request.method == 'POST':
        colaborador.nome = request.form['nome']
        colaborador.empresa_id = request.form['empresa']
        colaborador.admissao = datetime.strptime(request.form['admissao'], '%Y-%m-%d')
        demissao = request.form['demissao']
        colaborador.demissao = datetime.strptime(demissao, '%Y-%m-%d') if demissao else None
        colaborador.empregador_id = request.form['empregador']
        colaborador.turno = request.form['turno']
        colaborador.coordenador_id = request.form['coordenador']
        colaborador.status = request.form['status']
        db.session.commit()
        flash('Colaborador atualizado!')
        return redirect(url_for('colaboradores'))
    return render_template('edit_colaborador.html', user=g.user, colaborador=colaborador, companies=companies,
                           empregadores=empregadores, coordenadores=coordenadores, turnos=turnos, status_list=status_list)

@app.route('/colaboradores/delete/<int:id>')
def delete_colaborador(id):
    if g.user is None:
        return redirect(url_for('login'))
    colaborador = Colaborador.query.get_or_404(id)
    db.session.delete(colaborador)
    db.session.commit()
    flash('Colaborador excluído!')
    return redirect(url_for('colaboradores'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Cria empresa "luft" se não existir
        if not Company.query.filter_by(name='luft').first():
            db.session.add(Company(name='luft'))
            db.session.commit()
        # Cria ou atualiza o usuário master
        master = User.query.filter_by(username=MASTER_USER).first()
        if not master:
            from werkzeug.security import generate_password_hash
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
            db.session.commit()
    app.run(debug=True)