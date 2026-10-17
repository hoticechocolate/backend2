from urllib.parse import quote
from .config import StorageConfig

class ImageService:
    def __init__(self, database, config: StorageConfig):
        self.collection = database.db.sic_maps
        self.config = config

    def dates(self):
        return list(self.collection.find({}, {'_id': 0, 'year': 1, 'month': 1}).sort([('year', 1), ('month', 1)]))

    def get(self, year: int, month: int):
        document = self.collection.find_one({'year': year, 'month': month}, {'_id': 0})
        if document is None:
            return None
        for kind in ['observed', 'predicted', 'error']:
            path = document.get(f'{kind}_path')
            document[f'{kind}_url'] = self.config.base_url.rstrip('/') + '/' + quote(path, safe='/') if path else None
        return document

class EvaluationService:
    def __init__(self, database):
        self.collection = database.db.model_evaluation

    def experiments(self):
        return list(self.collection.find({}, {'_id': 0, 'experiment_id': 1}).sort('experiment_id', 1))

    def get(self, experiment_id):
        return self.collection.find_one({'experiment_id': experiment_id}, {'_id': 0})
