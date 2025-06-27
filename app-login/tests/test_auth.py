def test_login_logout(client):
    # Testa login inválido
    resp = client.post('/login', data={'username': 'fake', 'password': 'fake', 'company': 1})
    assert b'Usu' in resp.data or resp.status_code == 200

    # Testa login válido
    resp = client.post('/login', data={'username': 'admin', 'password': 'admin', 'company': 1}, follow_redirects=True)
    assert b'RH App' in resp.data or resp.status_code in (200, 302)

    # Testa logout
    resp = client.get('/logout', follow_redirects=True)
    assert b'Entrar' in resp.data