def test_register_sector_page(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin', 'company': 1})
    resp = client.get('/register_sector')
    assert resp.status_code == 200

def test_add_sector(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin', 'company': 1})
    resp = client.post('/register_sector', data={'setor': 'Novo Setor'}, follow_redirects=True)
    assert b'Setor cadastrado' in resp.data or b'Setor atualizado' in resp.data