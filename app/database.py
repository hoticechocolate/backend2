from pymongo import MongoClient, ASCENDING
from .config import DatabaseConfig

class Database:
    def __init__(self, config: DatabaseConfig):
        self.client = MongoClient(config.uri, serverSelectionTimeoutMS=3000, tz_aware=True)
        self.db = self.client[config.name]

    def initialize(self):
        self.client.admin.command('ping')
        definitions = {
            'sic_maps': {
                'required': ['year', 'month'],
                'properties': {'year': {'bsonType': 'int', 'minimum': 1900, 'maximum': 2200},
                               'month': {'bsonType': 'int', 'minimum': 1, 'maximum': 12},
                               **{key: {'bsonType': ['string', 'null']} for key in ['observed_path', 'predicted_path', 'error_path']}},
            },
            'model_evaluation': {
                'required': ['experiment_id', 'learning_curve', 'classification_metrics'],
                'properties': {'experiment_id': {'bsonType': 'string', 'minLength': 1},
                               'learning_curve': {'bsonType': 'object'},
                               'classification_metrics': {'bsonType': 'object'},
                               'monthly_metrics': {'bsonType': ['array', 'null']}},
            },
        }
        existing = self.db.list_collection_names()
        for name, schema in definitions.items():
            validator = {'$jsonSchema': {'bsonType': 'object', **schema}}
            if name not in existing:
                self.db.create_collection(name, validator=validator)
            else:
                self.db.command('collMod', name, validator=validator, validationLevel='strict')
        self.db.sic_maps.create_index([('year', ASCENDING), ('month', ASCENDING)], unique=True)
        self.db.model_evaluation.create_index('experiment_id', unique=True)

    def close(self):
        self.client.close()
