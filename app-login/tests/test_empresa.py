def test_register_company_page(client):
    resp = client.get('/register_company')
    assert resp.status_code in (200, 302)

# def test_add_company(client):
#     resp = client.post('/register_company', data={'name': 'Nova Empresa'}, follow_redirects=True)
#     assert b'Empresa cadastrada' in resp.data