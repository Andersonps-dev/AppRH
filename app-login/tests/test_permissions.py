def test_permissions_page(client):
    resp = client.get('/permissions')
    assert resp.status_code in (200, 302)