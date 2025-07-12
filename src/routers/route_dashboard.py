# src/routers/route_dashboard.py

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from src.database.db import get_db
from src.database import models
from src.repositorios.dashboard import RepositorioDashboard
from src.utils.api_response import success_response, error_response
from src.utils.auth_utils import obter_usuario_logado
from src.utils.route_error_handler import RouteErrorHandler
from typing import Optional

# A tag 'Dashboard (BI)' será usada para agrupar todas as rotas na documentação.
# O arquivo server.py também agrupa sob a tag "dashboard".
router = APIRouter(route_class=RouteErrorHandler)

@router.get("/dashboard/kpis-gerais", tags=['Dashboard (BI)'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def get_kpis_gerais(db: Session = Depends(get_db), usuario = Depends(obter_usuario_logado)):
    """Retorna os principais indicadores de performance (KPIs) do sistema."""
    try:
        dados = await RepositorioDashboard(db).get_kpis_gerais()
        return success_response(dados, "KPIs gerais carregados com sucesso.")
    except Exception as e:
        return error_response(message=f"Erro ao buscar KPIs: {e}")

@router.get("/dashboard/distribuicao-competidores/estado", tags=['Dashboard (BI)'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def get_distribuicao_competidores_por_estado(db: Session = Depends(get_db), usuario = Depends(obter_usuario_logado)):
    """Retorna a distribuição geográfica dos competidores por estado."""
    try:
        dados = await RepositorioDashboard(db).get_distribuicao_competidores_por_estado()
        return success_response(dados, "Distribuição de competidores por estado carregada.")
    except Exception as e:
        return error_response(message=f"Erro ao buscar dados: {e}")

@router.get("/dashboard/distribuicao-competidores/handicap", tags=['Dashboard (BI)'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def get_distribuicao_competidores_por_handicap(db: Session = Depends(get_db), usuario = Depends(obter_usuario_logado)):
    """Retorna a quantidade de competidores em cada nível de handicap."""
    try:
        dados = await RepositorioDashboard(db).get_distribuicao_competidores_por_handicap()
        return success_response(dados, "Distribuição de competidores por handicap carregada.")
    except Exception as e:
        return error_response(message=f"Erro ao buscar dados: {e}")

@router.get("/dashboard/distribuicao-competidores/idade", tags=['Dashboard (BI)'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def get_distribuicao_competidores_por_idade(db: Session = Depends(get_db), usuario = Depends(obter_usuario_logado)):
    """Retorna a distribuição de competidores por faixas de idade."""
    try:
        dados = await RepositorioDashboard(db).get_distribuicao_competidores_por_idade()
        return success_response(dados, "Distribuição de competidores por idade carregada.")
    except Exception as e:
        return error_response(message=f"Erro ao buscar dados: {e}")

@router.get("/dashboard/participacao/por-categoria", tags=['Dashboard (BI)'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def get_participacao_por_categoria(db: Session = Depends(get_db), usuario = Depends(obter_usuario_logado)):
    """Retorna o número de trios inscritos por categoria."""
    try:
        dados = await RepositorioDashboard(db).get_participacao_por_categoria()
        return success_response(dados, "Dados de participação por categoria carregados.")
    except Exception as e:
        return error_response(message=f"Erro ao buscar dados: {e}")

@router.get("/dashboard/evolucao/provas-no-tempo", tags=['Dashboard (BI)'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def get_evolucao_provas_no_tempo(ano: Optional[int] = Query(None, description="Filtre os resultados para um ano específico."), db: Session = Depends(get_db), usuario = Depends(obter_usuario_logado)):
    """Retorna a quantidade de provas realizadas ao longo do tempo."""
    try:
        dados = await RepositorioDashboard(db).get_evolucao_provas_no_tempo(ano)
        return success_response(dados, "Evolução de provas no tempo carregada.")
    except Exception as e:
        return error_response(message=f"Erro ao buscar dados: {e}")

@router.get("/dashboard/ranking/top-premiacao", tags=['Dashboard (BI)'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def get_ranking_premiacao_competidores(limit: int = Query(10, description="Número de posições no ranking a serem retornadas.", ge=1, le=50), db: Session = Depends(get_db), usuario = Depends(obter_usuario_logado)):
    """Retorna o ranking dos competidores que mais ganharam prêmios."""
    try:
        dados = await RepositorioDashboard(db).get_ranking_premiacao_competidores(limit)
        return success_response(dados, f"Top {limit} competidores por premiação carregado.")
    except Exception as e:
        return error_response(message=f"Erro ao buscar dados: {e}")

@router.get("/dashboard/estatisticas/passadas", tags=['Dashboard (BI)'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def get_estatisticas_passadas(db: Session = Depends(get_db), usuario = Depends(obter_usuario_logado)):
    """Retorna dados agregados sobre as passadas (tempo médio, status, etc.)."""
    try:
        dados = await RepositorioDashboard(db).get_estatisticas_passadas()
        return success_response(dados, "Estatísticas de passadas carregadas com sucesso.")
    except Exception as e:
        return error_response(message=f"Erro ao buscar dados: {e}")