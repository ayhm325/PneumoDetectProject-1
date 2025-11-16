import os
import pytest
from app import create_app, db

@pytest.fixture
def app():
    # Ensure ML-heavy imports are skipped during tests
    os.environ['SKIP_ML'] = '1'
    cfg = {'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'}
    app = create_app(cfg)

    # Create DB schema for tests
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
