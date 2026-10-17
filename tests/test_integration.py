"""Run against a real MongoDB using a unique disposable database."""
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError, WriteError
from app.config import Settings, ROOT
from app.database import Database
from app.importer import import_files, parse_csv
from app.models import SicMap
from app.api import create_app

@pytest.fixture
def context():
    settings = Settings.load()
    settings.database.name = 'polarice_test_' + uuid4().hex
    database = Database(settings.database)
    try:
        counts = import_files(database, ROOT / 'imports/sic_maps_rows.csv', ROOT / 'imports/model_evaluation_rows.csv')
        yield settings, database, counts
    finally:
        database.client.drop_database(settings.database.name)
        database.close()

def test_import_and_database_constraints(context):
    settings, database, counts = context
    repeated = import_files(database, ROOT / 'imports/sic_maps_rows.csv', ROOT / 'imports/model_evaluation_rows.csv')
    assert counts == repeated
    assert database.db.sic_maps.count_documents({}) == counts['sic_maps']
    assert database.db.model_evaluation.count_documents({}) == counts['model_evaluation']
    sample = database.db.sic_maps.find_one()
    sample.pop('_id')
    with pytest.raises(DuplicateKeyError):
        database.db.sic_maps.insert_one(sample)
    with pytest.raises(WriteError):
        database.db.sic_maps.insert_one({'year': 2026, 'month': 13})
    evaluation = database.db.model_evaluation.find_one()
    assert isinstance(evaluation['learning_curve'], dict)
    assert isinstance(evaluation['monthly_metrics'], list)

def test_public_api(context):
    settings, database, counts = context
    with TestClient(create_app(settings)) as client:
        assert client.get('/health').status_code == 200
        dates = client.get('/api/sic-maps/dates').json()
        assert len(dates) == counts['sic_maps']
        result = client.get('/api/sic-maps', params={'year': 2025, 'month': 9})
        assert result.status_code == 200
        for kind in ['observed', 'predicted', 'error']:
            assert result.json()[f'{kind}_url'] == f'{settings.storage.base_url}/{kind}/2025-09_sic_values_{kind}.png'
        assert client.get('/api/sic-maps', params={'year': 2025, 'month': 13}).status_code == 422
        assert client.get('/api/sic-maps', params={'year': 1900, 'month': 1}).status_code == 404
        experiments = client.get('/api/evaluations').json()
        assert len(experiments) == counts['model_evaluation']
        assert client.get('/api/evaluations/' + experiments[0]['experiment_id']).json()['learning_curve']
        assert client.get('/api/evaluations/missing').status_code == 404
        assert client.get('/status').status_code == 404
        assert len(client.get('/compat/rest/v1/sic_maps?select=*&order=year.asc,month.asc').json()) == counts['sic_maps']
        assert len(client.get('/compat/rest/v1/model_evaluation?select=*&order=created_at.desc&limit=1').json()) == 1

def test_admin_authentication(context, monkeypatch):
    settings, database, counts = context
    monkeypatch.setenv(settings.admin.token_env, 'test-only-secret-at-least-24-chars')
    with TestClient(create_app(settings, admin=True)) as client:
        assert client.get('/status').status_code == 401
        assert client.get('/status', headers={'Authorization': 'Bearer wrong'}).status_code == 401
        auth = {'Authorization': 'Bearer test-only-secret-at-least-24-chars'}
        assert client.get('/status', headers=auth).json() == counts
        assert client.get('/docs', headers=auth).status_code == 404

def test_invalid_import_does_not_write(context, tmp_path):
    settings, database, counts = context
    invalid = tmp_path / 'invalid.csv'
    invalid.write_text('year,month\n2025,13\n', encoding='utf-8')
    with pytest.raises(ValueError):
        import_files(database, invalid, ROOT / 'imports/model_evaluation_rows.csv')
    assert database.db.sic_maps.count_documents({}) == counts['sic_maps']
