import pytest
import tempfile
import os
from app import create_app, db
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost.localdomain'


@pytest.fixture
def app():
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def temp_test_files():
    with tempfile.TemporaryDirectory() as temp_dir:
        test_txt = os.path.join(temp_dir, 'test.txt')
        with open(test_txt, 'w', encoding='utf-8') as f:
            f.write('Test Dosyası İçeriği')
        
        yield temp_dir
