def test_export_colaboradores(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin', 'company': 1})
    resp = client.get('/export_colaboradores')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/octet-stream']