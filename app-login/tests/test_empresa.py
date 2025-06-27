def test_register_company_page(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin', 'company': 1})
    resp = client.get('/register_company')
    assert resp.status_code == 200

def test_add_company(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin', 'company': 1})
    resp = client.post('/register_company', data={'name': 'Nova Empresa'}, follow_redirects=True)
    assert b'Empresa cadastrada' in resp.data or b'Empresa atualizada' in resp.data