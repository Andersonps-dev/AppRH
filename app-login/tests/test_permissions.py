def test_permissions_page(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin', 'company': 1})
    resp = client.get('/permissions')
    assert resp.status_code == 200