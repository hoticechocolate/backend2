"""Generate per-deployment secrets without printing them or overwriting .env."""
from pathlib import Path
import secrets

target = Path(__file__).resolve().parents[1] / '.env'
with target.open('x', encoding='utf-8') as stream:
    stream.write('POLARICE_HTTP_PORT=8080\nMONGO_ROOT_USERNAME=polarice_owner\n')
    stream.write('MONGO_ROOT_PASSWORD=' + secrets.token_urlsafe(36) + '\n')
    stream.write('POLARICE_ADMIN_TOKEN=' + secrets.token_urlsafe(36) + '\n')
print('Created backend/.env with unique database and administrator secrets.')
