import argparse
import json
from pathlib import Path
from app.config import Settings, ROOT
from app.database import Database
from app.importer import import_files

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['init-db', 'import-data', 'web', 'admin'])
    parser.add_argument('--config')
    parser.add_argument('--maps', type=Path, default=ROOT / 'imports/sic_maps_rows.csv')
    parser.add_argument('--evaluations', type=Path, default=ROOT / 'imports/model_evaluation_rows.csv')
    args = parser.parse_args()
    settings = Settings.load(args.config)
    if args.command in ['web', 'admin']:
        import uvicorn
        from app.api import create_app
        network = settings.admin if args.command == 'admin' else settings.web
        uvicorn.run(create_app(settings, admin=args.command == 'admin'), host=network.host, port=network.port)
        return
    database = Database(settings.database)
    try:
        if args.command == 'init-db':
            database.initialize()
            print('Database schemas and indexes initialized')
        else:
            print(json.dumps(import_files(database, args.maps, args.evaluations)))
    finally:
        database.close()

if __name__ == '__main__':
    main()
