"""Start project-local MongoDB, import CSV, run tests and live HTTP smoke checks."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import httpx
from pymongo import MongoClient
from app.config import ROOT, Settings

def free_port():
    with socket.socket() as stream:
        stream.bind(('127.0.0.1', 0))
        return stream.getsockname()[1]

def main():
    runtime = ROOT / '.runtime'
    mongo = next(runtime.glob('*/bin/mongod.exe'))
    data = runtime / 'db'
    data.mkdir(exist_ok=True)
    processes = []
    handles = []
    settings = Settings.load()
    mongo_port = free_port()
    settings.database.uri = f'mongodb://127.0.0.1:{mongo_port}'
    settings.web.port = free_port()
    settings.admin.port = free_port()
    config = runtime / 'verification.json'
    config.write_text(settings.model_dump_json(indent=2), encoding='utf-8')
    environment = dict(os.environ, POLARICE_CONFIG=str(config), POLARICE_ADMIN_TOKEN=secrets.token_urlsafe(32))
    try:
        processes.append(subprocess.Popen([str(mongo), '--dbpath', str(data), '--bind_ip', '127.0.0.1', '--port', str(mongo_port), '--logpath', str(runtime / 'mongod.log'), '--logappend'], creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)))
        with MongoClient(settings.database.uri, serverSelectionTimeoutMS=15000) as client:
            client.admin.command('ping')
        subprocess.run([sys.executable, 'manage.py', 'import-data'], cwd=ROOT, env=environment, check=True)
        subprocess.run([sys.executable, '-m', 'pytest', '-q'], cwd=ROOT, env=environment, check=True)
        for kind in ['web', 'admin']:
            log = (runtime / f'{kind}.log').open('w', encoding='utf-8')
            handles.append(log)
            processes.append(subprocess.Popen([sys.executable, 'manage.py', kind], cwd=ROOT, env=environment, stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)))
        web = f'http://127.0.0.1:{settings.web.port}'
        admin = f'http://127.0.0.1:{settings.admin.port}'
        with httpx.Client(trust_env=False, timeout=5) as client:
            for address, headers in [(web, {}), (admin, {'Authorization': 'Bearer ' + environment['POLARICE_ADMIN_TOKEN']})]:
                for attempt in range(100):
                    try:
                        response = client.get(address + '/health', headers=headers)
                        response.raise_for_status()
                        break
                    except httpx.HTTPError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError('HTTP server failed to start')
            result = client.get(web + '/api/sic-maps', params={'year': 2025, 'month': 9})
            result.raise_for_status()
            assert client.get(admin + '/status').status_code == 401
            status = client.get(admin + '/status', headers={'Authorization': 'Bearer ' + environment['POLARICE_ADMIN_TOKEN']})
            status.raise_for_status()
            report = {'status': 'passed', 'database': settings.database.name, 'records': status.json(), 'sample': result.json(), 'live_http': True, 'tests': 4}
            (ROOT / 'test-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({'live_http': 'passed', 'records': status.json()}))
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=20)
        for handle in handles:
            handle.close()

if __name__ == '__main__':
    main()
