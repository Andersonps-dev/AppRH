import pytest
from app import app, db
from models import Company, User, Permission
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            company = Company(name='LUFT')
            db.session.add(company)
            db.session.commit()
            user = User(username='admin', password=generate_password_hash('admin'), company_id=company.id, role='admin')
            db.session.add(user)
            db.session.commit()
            # Permissões básicas para admin
            perm = Permission(role='admin', can_access_index=True, can_access_register_person=True, can_access_register_company=True, can_access_colaboradores=True, can_access_lista_presenca=True, can_access_register_sector=True, can_access_permissions=True)
            db.session.add(perm)
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()

def test_login(client):
    response = client.post('/login', data={'username': 'admin', 'password': 'admin', 'company': 1})
    assert response.status_code == 200
    assert b'Login successful' in response.data