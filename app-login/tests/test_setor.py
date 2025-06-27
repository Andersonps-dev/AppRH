def test_register_sector_page(client):
    resp = client.get('/register_sector')
    assert resp.status_code in (200, 302)

# def test_add_sector(client):
#     resp = client.post('/register_sector', data={'setor': 'Novo Setor'}, follow_redirects=True)
#     assert b'Setor cadastrado' in resp.data