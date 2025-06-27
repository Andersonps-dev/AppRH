def test_colaboradores_page(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin', 'company': 1})
    resp = client.get('/colaboradores')
    assert resp.status_code == 200

def test_add_colaborador(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin', 'company': 1})
    # Busca ids válidos
    from models import Setor, Company
    with client.application.app_context():
        setor = Setor.query.first()
        empresa = Company.query.first()
    resp = client.post('/add_colaborador', data={
        'nome': 'Teste',
        'cpf': '12345678900',
        'funcao': 'Analista',
        'admissao': '2020-01-01',
        'setor_id': setor.id,
        'turno': '1º TURNO',
        'empregador': 'LUFT',
        'situacao': 'ATIVO',
        'empresa_id': empresa.id,
        'gestor': 'Gestor'
    }, follow_redirects=True)
    assert b'Colaborador cadastrado' in resp.data