import os
import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from .config import Settings
from .database import Database
from .services import ImageService, EvaluationService

def create_app(settings: Settings, admin: bool = False):
    token = os.environ.get(settings.admin.token_env, '') if admin else ''
    if admin and len(token) < 24:
        raise ValueError(f'Set {settings.admin.token_env} to a secret of at least 24 characters')

    @asynccontextmanager
    async def lifespan(app):
        database = Database(settings.database)
        try:
            database.client.admin.command('ping')
            app.state.database = database
            app.state.images = ImageService(database, settings.storage)
            app.state.evaluations = EvaluationService(database)
            yield
        finally:
            database.close()

    def authorize(authorization: str | None = Header(default=None)):
        if not secrets.compare_digest(authorization or '', f'Bearer {token}'):
            raise HTTPException(401, 'Administrator authentication required')

    app = FastAPI(title='polarice admin' if admin else 'polarice API', lifespan=lifespan,
                  docs_url=None if admin else '/docs', redoc_url=None, openapi_url=None if admin else '/openapi.json',
                  dependencies=[Depends(authorize)] if admin else [])
    if not admin and settings.web.allowed_origins:
        app.add_middleware(CORSMiddleware, allow_origins=settings.web.allowed_origins, allow_methods=['GET'], allow_headers=['*'])

    @app.exception_handler(PyMongoError)
    async def database_error(request, error):
        return JSONResponse(status_code=503, content={'detail': 'Database temporarily unavailable'})

    @app.get('/health')
    def health():
        app.state.database.client.admin.command('ping')
        return {'status': 'ok'}

    if admin:
        @app.get('/status')
        def status():
            db = app.state.database.db
            return {'sic_maps': db.sic_maps.count_documents({}), 'model_evaluation': db.model_evaluation.count_documents({})}
    else:
        # Compatibility endpoints for the existing read-only frontend. No Supabase DB calls.
        @app.get('/compat/rest/v1/sic_maps')
        def frontend_maps():
            return list(app.state.database.db.sic_maps.find({}, {'_id': 0}).sort([('year', 1), ('month', 1)]))

        @app.get('/compat/rest/v1/model_evaluation')
        def frontend_evaluation():
            return list(app.state.database.db.model_evaluation.find({}, {'_id': 0}).sort('created_at', -1).limit(1))

        @app.get('/api/sic-maps/dates')
        def dates():
            return app.state.images.dates()

        @app.get('/api/sic-maps')
        def image(year: int = Query(ge=1900, le=2200), month: int = Query(ge=1, le=12)):
            result = app.state.images.get(year, month)
            if result is None:
                raise HTTPException(404, 'No images registered for this month')
            return result

        @app.get('/api/evaluations')
        def evaluations():
            return app.state.evaluations.experiments()

        @app.get('/api/evaluations/{experiment_id}')
        def evaluation(experiment_id: str):
            result = app.state.evaluations.get(experiment_id)
            if result is None:
                raise HTTPException(404, 'Experiment not found')
            return result
    return app
