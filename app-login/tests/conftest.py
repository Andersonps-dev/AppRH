import pytest
from app import app, db
from models import Company, User
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
            user = User(username='admin', password=generate_password_hash('admin'), company_id=company.id)
            db.session.add(user)
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()