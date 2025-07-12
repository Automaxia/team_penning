from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import Session
from src.database import models, schemas
from src.utils.error_handler import handle_error
from datetime import date, datetime
from typing import Dict, Any, List, Optional

class RepositorioDashboard:
    """
    Repositório para buscar dados agregados para o dashboard de BI.
    """

    def __init__(self, db: Session):
        self.db = db

    async def get_kpis_gerais(self) -> Dict[str, Any]:
        """
        Busca os Key Performance Indicators (KPIs) gerais do sistema.
        """
        try:
            total_competidores = self.db.execute(select(func.count(schemas.Competidores.id)).where(schemas.Competidores.ativo == True)).scalar()
            total_provas = self.db.execute(select(func.count(schemas.Provas.id)).where(schemas.Provas.ativa == True)).scalar()
            total_categorias = self.db.execute(select(func.count(schemas.Categorias.id)).where(schemas.Categorias.ativa == True)).scalar()
            total_trios = self.db.execute(select(func.count(schemas.Trios.id))).scalar()

            return {
                "total_competidores_ativos": total_competidores or 0,
                "total_provas_realizadas": total_provas or 0,
                "total_categorias_ativas": total_categorias or 0,
                "total_trios_formados": total_trios or 0,
            }
        except Exception as error:
            handle_error(error, self.get_kpis_gerais)

    async def get_distribuicao_competidores_por_estado(self) -> List[Dict[str, Any]]:
        """
        Retorna a contagem de competidores agrupados por estado.
        Ideal para um gráfico de mapa.
        """
        try:
            stmt = select(
                schemas.Competidores.estado,
                func.count(schemas.Competidores.id).label("total")
            ).where(
                schemas.Competidores.ativo == True,
                schemas.Competidores.estado.isnot(None)
            ).group_by(
                schemas.Competidores.estado
            ).order_by(
                desc("total")
            )
            resultado = self.db.execute(stmt).all()
            return [{"estado": row.estado, "total_competidores": row.total} for row in resultado]
        except Exception as error:
            handle_error(error, self.get_distribuicao_competidores_por_estado)

    async def get_distribuicao_competidores_por_handicap(self) -> List[Dict[str, Any]]:
        """
        Retorna a contagem de competidores por faixa de handicap.
        Ideal para um gráfico de barras.
        """
        try:
            stmt = select(
                schemas.Competidores.handicap,
                func.count(schemas.Competidores.id).label("total")
            ).where(
                schemas.Competidores.ativo == True
            ).group_by(
                schemas.Competidores.handicap
            ).order_by(
                schemas.Competidores.handicap
            )
            resultado = self.db.execute(stmt).all()
            return [{"handicap": row.handicap, "total_competidores": row.total} for row in resultado]
        except Exception as error:
            handle_error(error, self.get_distribuicao_competidores_por_handicap)
            
    async def get_distribuicao_competidores_por_idade(self) -> List[Dict[str, Any]]:
        """
        Retorna a contagem de competidores por faixa etária.
        Ideal para um gráfico de colunas.
        """
        try:
            today = date.today()
            faixas = [
                {"nome": "Até 12", "filtro": and_(func.extract('year', today) - func.extract('year', schemas.Competidores.data_nascimento) <= 12)},
                {"nome": "13-17", "filtro": and_((func.extract('year', today) - func.extract('year', schemas.Competidores.data_nascimento)).between(13, 17))},
                {"nome": "18-30", "filtro": and_((func.extract('year', today) - func.extract('year', schemas.Competidores.data_nascimento)).between(18, 30))},
                {"nome": "31-45", "filtro": and_((func.extract('year', today) - func.extract('year', schemas.Competidores.data_nascimento)).between(31, 45))},
                {"nome": "46+", "filtro": and_(func.extract('year', today) - func.extract('year', schemas.Competidores.data_nascimento) > 45)},
            ]

            resultado = []
            for faixa in faixas:
                count = self.db.execute(
                    select(func.count(schemas.Competidores.id))
                    .where(schemas.Competidores.ativo == True, faixa["filtro"])
                ).scalar()
                resultado.append({"faixa_etaria": faixa["nome"], "total_competidores": count or 0})

            return resultado
        except Exception as error:
            handle_error(error, self.get_distribuicao_competidores_por_idade)


    async def get_participacao_por_categoria(self) -> List[Dict[str, Any]]:
        """
        Retorna o número de trios (participações) por categoria.
        Ideal para um gráfico de pizza ou funil.
        """
        try:
            stmt = select(
                schemas.Categorias.nome,
                schemas.Categorias.tipo,
                func.count(schemas.Trios.id).label("total_trios")
            ).join(
                schemas.Trios, schemas.Categorias.id == schemas.Trios.categoria_id
            ).group_by(
                schemas.Categorias.nome,
                schemas.Categorias.tipo
            ).order_by(
                desc("total_trios")
            )
            resultado = self.db.execute(stmt).all()
            return [{"categoria_nome": row.nome, "categoria_tipo": row.tipo, "total_trios": row.total_trios} for row in resultado]
        except Exception as error:
            handle_error(error, self.get_participacao_por_categoria)

    async def get_evolucao_provas_no_tempo(self, ano: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retorna a quantidade de provas realizadas por mês/ano.
        Ideal para um gráfico de linhas.
        """
        try:
            filtro_ano = func.extract('year', schemas.Provas.data) == ano if ano else func.extract('year', schemas.Provas.data) <= datetime.now().year

            stmt = select(
                func.extract('year', schemas.Provas.data).label("ano"),
                func.extract('month', schemas.Provas.data).label("mes"),
                func.count(schemas.Provas.id).label("total_provas")
            ).where(
                filtro_ano
            ).group_by(
                "ano", "mes"
            ).order_by(
                "ano", "mes"
            )
            resultado = self.db.execute(stmt).all()
            return [{"ano": row.ano, "mes": row.mes, "total_provas": row.total_provas} for row in resultado]
        except Exception as error:
            handle_error(error, self.get_evolucao_provas_no_tempo)
            
    async def get_ranking_premiacao_competidores(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna o ranking dos competidores que mais receberam prêmios.
        Ideal para um Top N em tabela ou gráfico de barras.
        """
        try:
            stmt = select(
                schemas.Competidores.nome,
                func.sum(schemas.Pontuacao.premiacao_valor).label("total_premiacao")
            ).join(
                schemas.Pontuacao, schemas.Competidores.id == schemas.Pontuacao.competidor_id
            ).group_by(
                schemas.Competidores.nome
            ).order_by(
                desc("total_premiacao")
            ).limit(limit)
            
            resultado = self.db.execute(stmt).all()
            return [{"competidor_nome": row.nome, "premiacao_total": float(row.total_premiacao or 0)} for row in resultado]
        except Exception as error:
            handle_error(error, self.get_ranking_premiacao_competidores)

    async def get_estatisticas_passadas(self) -> Dict[str, Any]:
        """
        Retorna estatísticas gerais sobre as passadas (tempos, status).
        Ideal para cartões de KPI e gráficos de pizza.
        """
        try:
            base_query = select(schemas.PassadasTrio)
            
            total_passadas = self.db.execute(select(func.count(schemas.PassadasTrio.id))).scalar()
            
            status_counts = self.db.execute(
                select(schemas.PassadasTrio.status, func.count(schemas.PassadasTrio.id))
                .group_by(schemas.PassadasTrio.status)
            ).all()

            tempo_medio = self.db.execute(
                select(func.avg(schemas.PassadasTrio.tempo_realizado))
                .where(schemas.PassadasTrio.tempo_realizado.isnot(None))
            ).scalar()

            distribuicao_status = {status: count for status, count in status_counts}

            return {
                "total_passadas_registradas": total_passadas or 0,
                "tempo_medio_execucao": float(tempo_medio or 0),
                "distribuicao_status": {
                    "pendente": distribuicao_status.get(schemas.StatusPassada.PENDENTE.value, 0),
                    "executada": distribuicao_status.get(schemas.StatusPassada.EXECUTADA.value, 0),
                    "no_time": distribuicao_status.get(schemas.StatusPassada.NO_TIME.value, 0),
                    "desclassificada": distribuicao_status.get(schemas.StatusPassada.DESCLASSIFICADA.value, 0),
                }
            }
        except Exception as error:
            handle_error(error, self.get_estatisticas_passadas)