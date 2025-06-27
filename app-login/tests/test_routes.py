def test_index_redirect(client):
    resp = client.get('/')
    assert resp.status_code == 302

def test_login_page(client):
    resp = client.get('/login')
    assert b'Entrar' in resp.data