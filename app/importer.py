import csv
import json
from datetime import datetime
from pathlib import Path
from .models import SicMap, Evaluation

def parse_csv(path: Path, model):
    documents = []
    keys = set()
    with path.open(encoding='utf-8-sig', newline='') as stream:
        for line, row in enumerate(csv.DictReader(stream), 2):
            try:
                row.pop('id', None)
                row = {key: (value if value != '' else None) for key, value in row.items()}
                if row.get('created_at'):
                    row['created_at'] = datetime.fromisoformat(row['created_at'])
                if model is Evaluation:
                    for key in ['learning_curve', 'classification_metrics', 'monthly_metrics']:
                        if row.get(key) is not None:
                            row[key] = json.loads(row[key])
                document = model.model_validate(row).model_dump()
                identity = (document['year'], document['month']) if model is SicMap else document['experiment_id']
                if identity in keys:
                    raise ValueError(f'Duplicate identity: {identity}')
                keys.add(identity)
                documents.append(document)
            except (ValueError, TypeError) as error:
                raise ValueError(f'{path.name}, row {line}: {error}') from error
    if not documents:
        raise ValueError(f'No data in {path.name}')
    return documents

def import_files(database, maps_path: Path, evaluations_path: Path):
    # Validate both files completely before any writes. Reimports update existing keys.
    maps = parse_csv(maps_path, SicMap)
    evaluations = parse_csv(evaluations_path, Evaluation)
    database.initialize()
    for document in maps:
        database.db.sic_maps.update_one({key: document[key] for key in ['year', 'month']}, {'$set': document}, upsert=True)
    for document in evaluations:
        database.db.model_evaluation.update_one({'experiment_id': document['experiment_id']}, {'$set': document}, upsert=True)
    return {'sic_maps': len(maps), 'model_evaluation': len(evaluations)}
