from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.applications import router as applications_router
from app.api.cases import router as cases_router
from app.api.investigations import router as investigations_router
from app.api.ai import router as ai_router
from app.api.reports import router as reports_router

app = FastAPI(title='AI Credit-Risk Investigation Agent API', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:3000','http://localhost:5173'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
app.include_router(applications_router, prefix='/applications', tags=['Applications'])
app.include_router(cases_router, prefix='/cases', tags=['Cases'])
app.include_router(investigations_router, prefix='/investigations', tags=['Investigations'])
app.include_router(ai_router, prefix='/ai', tags=['AI Interfaces'])
app.include_router(reports_router, prefix='/reports', tags=['Reports'])

@app.get('/')
def root(): return {'name': app.title, 'status': 'running', 'docs': '/docs'}
@app.get('/health')
def health(): return {'status': 'healthy'}
