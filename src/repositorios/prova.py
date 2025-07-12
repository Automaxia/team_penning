from sqlalchemy import select, delete, update, func, desc, asc, and_, or_, extract, text
from sqlalchemy.orm import Session, joinedload
from src.database import models, schemas
from src.utils.error_handler import handle_error
from src.utils.utils_lctp import UtilsLCTP
from src.utils.config_lctp import ConfigLCTP
from src.utils.exceptions_lctp import LCTPException
from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any, Tuple
import pytz

AMSP = pytz.timezone('America/Sao_Paulo')

class RepositorioProva:
    """Repositório para operações com provas do sistema LCTP"""
    
    def __init__(self, db: Session):
        self.db = db

    async def get_all(self, ativas_apenas: bool = True, ano: Optional[int] = None) -> List[Dict]:
        """Versão que retorna dicionários em vez de objetos schemas"""
        
        query_sql = """
        SELECT 
            p.id,
            p.nome,
            p.data,
            p.rancho,
            p.cidade,
            p.estado,
            p.valor_inscricao,
            p.percentual_desconto,
            p.ativa,
            p.tipo_copa,
            p.created_at,
            p.updated_at,
            
            -- Contagens
            COUNT(DISTINCT t.id) as total_trios,
            COUNT(DISTINCT it.competidor_id) as total_competidores,
            COUNT(DISTINCT t.categoria_id) as total_categorias,
            
            -- Informações adicionais úteis
            COUNT(DISTINCT CASE WHEN t.status = 'ativo' THEN t.id END) as trios_ativos,
            COUNT(DISTINCT CASE WHEN t.status = 'no_time' THEN t.id END) as trios_no_time,
            COUNT(DISTINCT CASE WHEN t.status = 'desclassificado' THEN t.id END) as trios_desclassificados,
            
            -- Status das passadas
            COUNT(DISTINCT pt.id) as total_passadas,
            COUNT(DISTINCT CASE WHEN pt.status = 'executada' THEN pt.id END) as passadas_executadas,
            COUNT(DISTINCT CASE WHEN pt.status = 'pendente' THEN pt.id END) as passadas_pendentes,
            
            -- Melhor tempo da prova
            MIN(pt.tempo_realizado) as melhor_tempo_prova
            
        FROM provas p
        LEFT JOIN trios t ON p.id = t.prova_id
        LEFT JOIN integrantes_trios it ON t.id = it.trio_id
        LEFT JOIN passadas_trio pt ON p.id = pt.prova_id
        
        WHERE p.deleted_at IS NULL
        """
        
        params = {}
        
        if ativas_apenas:
            query_sql += " AND p.ativa = :ativa"
            params['ativa'] = True
        
        if ano:
            query_sql += " AND EXTRACT(YEAR FROM p.data) = :ano"
            params['ano'] = ano
        
        query_sql += """
        GROUP BY 
            p.id, p.nome, p.data, p.rancho, p.cidade, p.estado,
            p.valor_inscricao, p.percentual_desconto, p.ativa, p.tipo_copa,
            p.created_at, p.updated_at
        ORDER BY p.data DESC
        """
        
        try:
            result = self.db.execute(text(query_sql), params).fetchall()
            
            # Converter para lista de dicionários
            #return [dict(row._mapping) for row in result]
            return result
            
        except Exception as error:
            handle_error(error, self.get_all)

    async def get_estatisticas(self, prova_id: int) -> Dict[str, Any]:
        """Obtém estatísticas detalhadas de uma prova específica"""
        try:
            # Query para contar trios
            total_trios = (
                self.db.query(func.count(schemas.Trios.id))
                .filter(schemas.Trios.prova_id == prova_id)
                .scalar() or 0
            )
            
            # Query para contar competidores únicos
            total_competidores = (
                self.db.query(func.count(distinct(schemas.TrioCompetidores.competidor_id)))
                .join(schemas.Trios, schemas.TrioCompetidores.trio_id == schemas.Trios.id)
                .filter(schemas.Trios.prova_id == prova_id)
                .scalar() or 0
            )
            
            # Query para contar categorias ativas na prova
            total_categorias = (
                self.db.query(func.count(distinct(schemas.Trios.categoria_id)))
                .filter(
                    and_(
                        schemas.Trios.prova_id == prova_id,
                        schemas.Trios.categoria_id.isnot(None)
                    )
                )
                .scalar() or 0
            )
            
            # Estatísticas por categoria
            stats_por_categoria = (
                self.db.query(
                    schemas.Categorias.nome.label('categoria'),
                    func.count(schemas.Trios.id).label('total_trios'),
                    func.count(distinct(schemas.TrioCompetidores.competidor_id)).label('total_competidores')
                )
                .select_from(schemas.Trios)
                .join(schemas.Categorias, schemas.Trios.categoria_id == schemas.Categorias.id)
                .join(schemas.TrioCompetidores, schemas.TrioCompetidores.trio_id == schemas.Trios.id)
                .filter(schemas.Trios.prova_id == prova_id)
                .group_by(schemas.Categorias.id, schemas.Categorias.nome)
                .all()
            )
            
            # Formatando estatísticas por categoria
            categorias_stats = []
            for stat in stats_por_categoria:
                categorias_stats.append({
                    'categoria': stat.categoria,
                    'total_trios': stat.total_trios,
                    'total_competidores': stat.total_competidores
                })
            
            return {
                'prova_id': prova_id,
                'total_trios': total_trios,
                'total_competidores': total_competidores,
                'total_categorias': total_categorias,
                'categorias_detalhes': categorias_stats,
                'media_competidores_por_trio': round(total_competidores / total_trios, 2) if total_trios > 0 else 0
            }
            
        except Exception as error:
            handle_error(error, self.get_estatisticas)
            return {
                'prova_id': prova_id,
                'total_trios': 0,
                'total_competidores': 0,
                'total_categorias': 0,
                'categorias_detalhes': [],
                'media_competidores_por_trio': 0
            }


    async def get_all_com_estatisticas(self, ativas_apenas: bool = True, ano: Optional[int] = None) -> List[Dict[str, Any]]:
        """Recupera todas as provas com suas estatísticas incluídas"""
        try:
            # Buscar todas as provas
            provas = await self.get_all(ativas_apenas, ano)
            
            provas_com_stats = []
            
            for prova in provas:
                # Converter prova para dict
                prova_dict = {
                    'id': prova.id,
                    'nome': prova.nome,
                    'data': prova.data,
                    'rancho': prova.rancho,
                    'cidade': prova.cidade,
                    'estado': prova.estado,
                    'valor_inscricao': prova.valor_inscricao,
                    'percentual_desconto': prova.percentual_desconto,
                    'tipo_copa': prova.tipo_copa,
                    'ativa': prova.ativa,
                    'created_at': prova.created_at,
                    'updated_at': prova.updated_at
                }
                
                # Adicionar estatísticas
                stats = await self.get_estatisticas(prova.id)
                prova_dict.update({
                    'estatisticas': {
                        'total_trios': stats['total_trios'],
                        'total_competidores': stats['total_competidores'],
                        'total_categorias': stats['total_categorias']
                    }
                })
                
                provas_com_stats.append(prova_dict)
            
            return provas_com_stats
            
        except Exception as error:
            handle_error(error, self.get_all_com_estatisticas)
            return []


    async def get_estatisticas_lote(self, prova_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Obtém estatísticas para múltiplas provas de uma só vez (otimizado)"""
        try:
            if not prova_ids:
                return {}
            
            # Query otimizada para buscar todas as estatísticas de uma vez
            stats_query = (
                self.db.query(
                    schemas.Trios.prova_id,
                    func.count(distinct(schemas.Trios.id)).label('total_trios'),
                    func.count(distinct(schemas.TrioCompetidores.competidor_id)).label('total_competidores'),
                    func.count(distinct(schemas.Trios.categoria_id)).label('total_categorias')
                )
                .select_from(schemas.Trios)
                .outerjoin(schemas.TrioCompetidores, schemas.TrioCompetidores.trio_id == schemas.Trios.id)
                .filter(schemas.Trios.prova_id.in_(prova_ids))
                .group_by(schemas.Trios.prova_id)
                .all()
            )
            
            # Organizar resultados por prova_id
            resultado = {}
            for stat in stats_query:
                resultado[stat.prova_id] = {
                    'total_trios': stat.total_trios,
                    'total_competidores': stat.total_competidores,
                    'total_categorias': stat.total_categorias if stat.total_categorias else 0
                }
            
            # Preencher provas sem dados com zeros
            for prova_id in prova_ids:
                if prova_id not in resultado:
                    resultado[prova_id] = {
                        'total_trios': 0,
                        'total_competidores': 0,
                        'total_categorias': 0
                    }
            
            return resultado
            
        except Exception as error:
            handle_error(error, self.get_estatisticas_lote)
            return {prova_id: {'total_trios': 0, 'total_competidores': 0, 'total_categorias': 0} for prova_id in prova_ids}

    async def get_by_id(self, prova_id: int) -> Optional[schemas.Provas]:
        """Recupera uma prova pelo ID"""
        try:
            stmt = select(schemas.Provas).options(
                joinedload(schemas.Provas.trios).joinedload(schemas.Trios.categoria),
                joinedload(schemas.Provas.resultados)
            ).where(schemas.Provas.id == prova_id)
            
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self.get_by_id)

    async def get_by_nome(self, nome: str) -> List[schemas.Provas]:
        """Busca provas por nome (busca parcial)"""
        try:
            stmt = select(schemas.Provas).where(
                schemas.Provas.nome.ilike(f"%{nome}%")
            ).order_by(desc(schemas.Provas.data))
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_by_nome)

    async def get_by_periodo(self, data_inicio: date, data_fim: date) -> List[schemas.Provas]:
        """Recupera provas de um período"""
        try:
            stmt = select(schemas.Provas).where(
                and_(
                    schemas.Provas.data >= data_inicio,
                    schemas.Provas.data <= data_fim
                )
            ).order_by(schemas.Provas.data)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_by_periodo)

    async def post(self, prova_data: models.ProvaPOST) -> schemas.Provas:
        """Cria uma nova prova"""
        try:
            # Validar data da prova
            if prova_data.data < date.today():
                raise LCTPException("Data da prova não pode ser no passado")

            db_prova = schemas.Provas(
                nome=prova_data.nome,
                data=prova_data.data,
                rancho=prova_data.rancho,
                cidade=prova_data.cidade,
                estado=prova_data.estado,
                valor_inscricao=prova_data.valor_inscricao,
                percentual_desconto=prova_data.percentual_desconto,
                ativa=prova_data.ativa,
                tipo_copa=prova_data.tipo_copa
            )

            self.db.add(db_prova)
            self.db.commit()
            self.db.refresh(db_prova)
            
            return db_prova
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.post)

    async def put(self, prova_id: int, prova_data: models.ProvaPUT) -> Optional[schemas.Provas]:
        """Atualiza uma prova"""
        try:
            prova_existente = await self.get_by_id(prova_id)
            if not prova_existente:
                raise LCTPException(f"Prova com ID {prova_id} não encontrada")

            # Verificar se pode alterar (não deve ter resultados se alterando data)
            if prova_data.data and prova_data.data != prova_existente.data:
                tem_resultados = await self._prova_tem_resultados(prova_id)
                if tem_resultados:
                    raise LCTPException("Não é possível alterar data de prova que já possui resultados")

            # Criar dicionário apenas com campos não None
            update_data = {k: v for k, v in prova_data.model_dump().items() if v is not None}
            update_data['updated_at'] = datetime.now(timezone.utc).astimezone(AMSP)
            
            if update_data:
                stmt = update(schemas.Provas).where(
                    schemas.Provas.id == prova_id
                ).values(**update_data)
                
                self.db.execute(stmt)
                self.db.commit()
            
            return await self.get_by_id(prova_id)
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.put)

    async def delete(self, prova_id: int) -> bool:
        """Remove uma prova (soft delete se tem trios/resultados)"""
        try:
            prova = await self.get_by_id(prova_id)
            if not prova:
                raise LCTPException(f"Prova com ID {prova_id} não encontrada")

            # Verificar se tem trios ou resultados
            tem_trios = await self._prova_tem_trios(prova_id)
            tem_resultados = await self._prova_tem_resultados(prova_id)

            if tem_trios or tem_resultados:
                # Soft delete - apenas marcar como inativa
                stmt = update(schemas.Provas).where(
                    schemas.Provas.id == prova_id
                ).values(
                    ativa=False,
                    deleted_at=datetime.now(timezone.utc).astimezone(AMSP)
                )
                
                self.db.execute(stmt)
                self.db.commit()
                return True
            else:
                # Delete físico se não tem dependências
                stmt = delete(schemas.Provas).where(
                    schemas.Provas.id == prova_id
                )
                
                self.db.execute(stmt)
                self.db.commit()
                return True
                
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.delete)

    # ---------------------- Consultas Especializadas ----------------------

    async def get_provas_por_rancho(self, rancho: str, ano: Optional[int] = None) -> List[schemas.Provas]:
        """Retorna provas de um rancho específico"""
        try:
            stmt = select(schemas.Provas).where(
                schemas.Provas.rancho.ilike(f"%{rancho}%")
            )
            
            if ano:
                stmt = stmt.where(extract('year', schemas.Provas.data) == ano)
            
            stmt = stmt.order_by(desc(schemas.Provas.data))
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_provas_por_rancho)

    async def get_provas_por_estado(self, estado: str, ano: Optional[int] = None) -> List[schemas.Provas]:
        """Retorna provas de um estado específico"""
        try:
            stmt = select(schemas.Provas).where(
                schemas.Provas.estado == estado.upper()
            )
            
            if ano:
                stmt = stmt.where(extract('year', schemas.Provas.data) == ano)
            
            stmt = stmt.order_by(desc(schemas.Provas.data))
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_provas_por_estado)

    async def get_provas_futuras(self) -> List[schemas.Provas]:
        """Retorna provas futuras (a partir de hoje)"""
        try:
            stmt = select(schemas.Provas).where(
                and_(
                    schemas.Provas.data >= date.today(),
                    schemas.Provas.ativa == True
                )
            ).order_by(schemas.Provas.data)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_provas_futuras)

    async def get_provas_passadas(self, limite: int = 50) -> List[schemas.Provas]:
        """Retorna provas passadas (mais recentes primeiro)"""
        try:
            stmt = select(schemas.Provas).where(
                schemas.Provas.data < date.today()
            ).order_by(
                desc(schemas.Provas.data)
            ).limit(limite)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_provas_passadas)

    async def get_estatisticas_prova(self, prova_id: int) -> Dict[str, Any]:
        """Gera estatísticas completas de uma prova"""
        try:
            prova = await self.get_by_id(prova_id)
            if not prova:
                return {}

            # Contar trios por categoria
            trios_por_categoria = self.db.execute(
                select(
                    schemas.Categorias.nome,
                    func.count(schemas.Trios.id).label('total_trios')
                ).join(
                    schemas.Trios
                ).where(
                    schemas.Trios.prova_id == prova_id
                ).group_by(
                    schemas.Categorias.id, schemas.Categorias.nome
                )
            ).all()

            # Total de competidores
            total_trios = sum(item.total_trios for item in trios_por_categoria)
            total_competidores = total_trios * 3

            # Análise de resultados
            resultados = self.db.execute(
                select(schemas.Resultados).where(
                    schemas.Resultados.prova_id == prova_id
                )
            ).scalars().all()

            trios_com_resultado = len(resultados)
            premiacao_total = sum(r.premiacao_valor or 0 for r in resultados)
            no_time_count = len([r for r in resultados if r.no_time])

            # Análise de tempos
            tempos_medios = [r.media_tempo for r in resultados if r.media_tempo]
            tempo_medio_geral = sum(tempos_medios) / len(tempos_medios) if tempos_medios else 0

            return {
                'prova': prova,
                'total_trios': total_trios,
                'total_competidores': total_competidores,
                'trios_por_categoria': dict(trios_por_categoria),
                'resultados': {
                    'trios_com_resultado': trios_com_resultado,
                    'premiacao_total': float(premiacao_total),
                    'no_time': no_time_count,
                    'tempo_medio_geral': round(tempo_medio_geral, 2) if tempo_medio_geral else None
                },
                'status_prova': 'realizada' if trios_com_resultado > 0 else 'programada'
            }
        except Exception as error:
            handle_error(error, self.get_estatisticas_prova)

    async def get_ranking_prova(self, prova_id: int, categoria_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Gera ranking de uma prova (geral ou por categoria)"""
        try:
            query = self.db.query(
                schemas.Resultados,
                schemas.Trios,
                schemas.Categorias.nome.label('categoria_nome')
            ).join(
                schemas.Trios,
                schemas.Resultados.trio_id == schemas.Trios.id
            ).join(
                schemas.Categorias,
                schemas.Trios.categoria_id == schemas.Categorias.id
            ).options(
                joinedload(schemas.Trios.integrantes).joinedload(schemas.IntegrantesTrios.competidor)
            ).filter(
                schemas.Resultados.prova_id == prova_id,
                schemas.Resultados.colocacao.isnot(None)
            )

            if categoria_id:
                query = query.filter(schemas.Trios.categoria_id == categoria_id)

            # Ordenar por colocação
            query = query.order_by(schemas.Resultados.colocacao.asc())

            resultados = query.all()
            
            ranking = []
            for resultado, trio, categoria_nome in resultados:
                ranking.append({
                    'colocacao': resultado.colocacao,
                    'trio': trio,
                    'categoria': categoria_nome,
                    'tempo_medio': resultado.media_tempo,
                    'premiacao': resultado.premiacao_valor,
                    'no_time': resultado.no_time
                })

            return ranking
        except Exception as error:
            handle_error(error, self.get_ranking_prova)

    # ---------------------- Relatórios ----------------------

    async def gerar_relatorio_anual(self, ano: int) -> Dict[str, Any]:
        """Gera relatório anual de provas"""
        try:
            provas_ano = await self.get_all(ativas_apenas=False, ano=ano)
            
            # Estatísticas básicas
            total_provas = len(provas_ano)
            provas_realizadas = 0
            total_trios = 0
            total_premiacao = 0
            
            # Análise por estado
            por_estado = {}
            por_mes = {}
            
            for prova in provas_ano:
                # Contar trios da prova
                trios_prova = self.db.execute(
                    select(func.count(schemas.Trios.id)).where(
                        schemas.Trios.prova_id == prova.id
                    )
                ).scalar()
                
                total_trios += trios_prova or 0
                
                # Verificar se foi realizada (tem resultados)
                tem_resultados = await self._prova_tem_resultados(prova.id)
                if tem_resultados:
                    provas_realizadas += 1
                    
                    # Somar premiação
                    premiacao_prova = self.db.execute(
                        select(func.sum(schemas.Resultados.premiacao_valor)).where(
                            schemas.Resultados.prova_id == prova.id
                        )
                    ).scalar()
                    
                    total_premiacao += float(premiacao_prova or 0)
                
                # Agrupar por estado
                estado = prova.estado or 'N/I'
                if estado not in por_estado:
                    por_estado[estado] = []
                por_estado[estado].append(prova)
                
                # Agrupar por mês
                mes = prova.data.month
                if mes not in por_mes:
                    por_mes[mes] = 0
                por_mes[mes] += 1

            return {
                'ano': ano,
                'total_provas': total_provas,
                'provas_realizadas': provas_realizadas,
                'provas_programadas': total_provas - provas_realizadas,
                'total_trios': total_trios,
                'total_competidores': total_trios * 3,
                'premiacao_total': total_premiacao,
                'por_estado': por_estado,
                'por_mes': por_mes,
                'media_trios_prova': round(total_trios / total_provas, 1) if total_provas > 0 else 0
            }
        except Exception as error:
            handle_error(error, self.gerar_relatorio_anual)

    async def get_calendario_provas(self, ano: int) -> Dict[str, List[schemas.Provas]]:
        """Retorna calendário de provas organizadas por mês"""
        try:
            provas_ano = await self.get_all(ativas_apenas=True, ano=ano)
            
            calendario = {}
            meses = [
                'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
            ]
            
            for prova in provas_ano:
                mes_nome = meses[prova.data.month - 1]
                if mes_nome not in calendario:
                    calendario[mes_nome] = []
                calendario[mes_nome].append(prova)
            
            # Ordenar provas dentro de cada mês
            for mes in calendario:
                calendario[mes].sort(key=lambda p: p.data)
            
            return calendario
        except Exception as error:
            handle_error(error, self.get_calendario_provas)

    # ---------------------- Validações e Utilitários ----------------------

    async def _prova_tem_trios(self, prova_id: int) -> bool:
        """Verifica se a prova tem trios inscritos"""
        try:
            count = self.db.execute(
                select(func.count(schemas.Trios.id)).where(
                    schemas.Trios.prova_id == prova_id
                )
            ).scalar()
            
            return count > 0
        except Exception as error:
            handle_error(error, self._prova_tem_trios)

    async def _prova_tem_resultados(self, prova_id: int) -> bool:
        """Verifica se a prova tem resultados"""
        try:
            count = self.db.execute(
                select(func.count(schemas.Resultados.id)).where(
                    schemas.Resultados.prova_id == prova_id
                )
            ).scalar()
            
            return count > 0
        except Exception as error:
            handle_error(error, self._prova_tem_resultados)

    async def pode_alterar_prova(self, prova_id: int) -> Tuple[bool, str]:
        """Verifica se a prova pode ser alterada"""
        try:
            prova = await self.get_by_id(prova_id)
            if not prova:
                return False, "Prova não encontrada"

            # Verificar se já passou
            if prova.data < date.today():
                tem_resultados = await self._prova_tem_resultados(prova_id)
                if tem_resultados:
                    return False, "Prova já realizada (possui resultados)"

            # Verificar trios inscritos
            tem_trios = await self._prova_tem_trios(prova_id)
            if tem_trios:
                return True, "Prova pode ser alterada, mas possui trios inscritos"

            return True, "Prova pode ser alterada livremente"
        except Exception as error:
            handle_error(error, self.pode_alterar_prova)

    async def duplicar_prova(self, prova_id: int, nova_data: date, novo_nome: Optional[str] = None) -> schemas.Provas:
        """Duplica uma prova para uma nova data"""
        try:
            prova_original = await self.get_by_id(prova_id)
            if not prova_original:
                raise LCTPException("Prova original não encontrada")

            # Criar nova prova baseada na original
            nova_prova_data = models.ProvaPOST(
                nome=novo_nome or f"{prova_original.nome} - CÓPIA",
                data=nova_data,
                rancho=prova_original.rancho,
                cidade=prova_original.cidade,
                estado=prova_original.estado,
                valor_inscricao=prova_original.valor_inscricao,
                percentual_desconto=prova_original.percentual_desconto,
                ativa=True,
                tipo_copa=prova_original.tipo_copa
            )

            nova_prova = await self.post(nova_prova_data)
            return nova_prova
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.duplicar_prova)

    async def get_provas_similares(self, prova_id: int, limite: int = 5) -> List[schemas.Provas]:
        """Encontra provas similares (mesmo rancho/cidade)"""
        try:
            prova = await self.get_by_id(prova_id)
            if not prova:
                return []

            stmt = select(schemas.Provas).where(
                and_(
                    schemas.Provas.id != prova_id,
                    or_(
                        schemas.Provas.rancho == prova.rancho,
                        and_(
                            schemas.Provas.cidade == prova.cidade,
                            schemas.Provas.estado == prova.estado
                        )
                    )
                )
            ).order_by(
                desc(schemas.Provas.data)
            ).limit(limite)

            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_provas_similares)

    # ---------------------- Exportação ----------------------

    async def exportar_provas(self, ano: Optional[int] = None, estado: Optional[str] = None) -> List[Dict[str, Any]]:
        """Exporta dados das provas em formato estruturado"""
        try:
            stmt = select(schemas.Provas)
            
            if ano:
                stmt = stmt.where(extract('year', schemas.Provas.data) == ano)
            
            if estado:
                stmt = stmt.where(schemas.Provas.estado == estado.upper())
            
            stmt = stmt.order_by(desc(schemas.Provas.data))
            
            provas = self.db.execute(stmt).scalars().all()
            
            export_data = []
            for prova in provas:
                # Buscar estatísticas básicas
                total_trios = self.db.execute(
                    select(func.count(schemas.Trios.id)).where(
                        schemas.Trios.prova_id == prova.id
                    )
                ).scalar()

                total_premiacao = self.db.execute(
                    select(func.sum(schemas.Resultados.premiacao_valor)).where(
                        schemas.Resultados.prova_id == prova.id
                    )
                ).scalar()

                prova_dict = {
                    'id': prova.id,
                    'nome': prova.nome,
                    'data': prova.data.isoformat(),
                    'rancho': prova.rancho,
                    'cidade': prova.cidade,
                    'estado': prova.estado,
                    'valor_inscricao': float(prova.valor_inscricao or 0),
                    'percentual_desconto': prova.percentual_desconto,
                    'tipo_copa': prova.tipo_copa.value if prova.tipo_copa else None,
                    'ativa': prova.ativa,
                    'total_trios': total_trios or 0,
                    'total_competidores': (total_trios or 0) * 3,
                    'premiacao_total': float(total_premiacao or 0),
                    'created_at': prova.created_at.isoformat() if prova.created_at else None
                }
                export_data.append(prova_dict)
            
            return export_data
        except Exception as error:
            handle_error(error, self.exportar_provas)