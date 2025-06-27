def test_colaboradores_page(client):
    resp = client.get('/colaboradores')
    assert resp.status_code in (200, 302)

# Para testar cadastro, descomente e ajuste conforme seu modelo e autenticação:
def test_add_colaborador(client):
    # Login
    client.post('/login', data={'username': 'admin', 'password': 'admin', 'company': 1})
    # Crie setor e empresa se necessário
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