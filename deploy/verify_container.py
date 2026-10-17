"""Smoke check the single published port without printing secrets."""
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

root = Path(__file__).resolve().parents[1]
values = dict(line.split('=', 1) for line in (root / '.env').read_text(encoding='utf-8').splitlines() if line and not line.startswith('#'))
base = 'http://127.0.0.1:' + values.get('POLARICE_HTTP_PORT', '8080')

def get(path, token=None):
    request = Request(base + path)
    if token:
        request.add_header('Authorization', 'Bearer ' + token)
    with urlopen(request, timeout=10) as response:
        return json.load(response)

assert get('/health')['status'] == 'ok'
with urlopen(Request(base + '/', method='HEAD'), timeout=10) as response:
    assert response.status == 200
    assert 'text/html' in response.headers.get('Content-Type', '')
assert len(get('/compat/rest/v1/sic_maps?select=*&order=year.asc,month.asc')) == 132
assert len(get('/compat/rest/v1/model_evaluation?select=*&order=created_at.desc&limit=1')) == 1
sample = get('/api/sic-maps?year=2025&month=9')
for kind in ['observed', 'predicted', 'error']:
    assert sample[kind + '_url'].endswith(f'/{kind}/2025-09_sic_values_{kind}.png')
try:
    get('/admin/status')
    raise AssertionError('Administrator endpoint accepted unauthenticated request')
except HTTPError as error:
    assert error.code == 401
status = get('/admin/status', values['POLARICE_ADMIN_TOKEN'])
assert status == {'sic_maps': 132, 'model_evaluation': 1}
print(json.dumps({'single_port': values.get('POLARICE_HTTP_PORT', '8080'), 'records': status, 'admin_auth': 'passed', 'status': 'passed'}))
