from sqlalchemy import select, delete, update, func, desc, asc, and_, or_, extract
from sqlalchemy.orm import Session, joinedload
from src.database import models, schemas
from src.utils.error_handler import handle_error
from src.utils.utils_lctp import UtilsLCTP
from src.utils.config_lctp import ConfigLCTP
from src.utils.exceptions_lctp import PontuacaoException, LCTPException
from datetime import datetime, timezone, date
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
import pytz

AMSP = pytz.timezone('America/Sao_Paulo')

class RepositorioPontuacao:
    """Repositório para operações com pontuação do sistema LCTP"""
    
    def __init__(self, db: Session):
        self.db = db

    # ---------------------- Operações Básicas ----------------------

    async def get_by_id(self, pontuacao_id: int) -> Optional[schemas.Pontuacao]:
        """Recupera uma pontuação pelo ID"""
        try:
            stmt = select(schemas.Pontuacao).options(
                joinedload(schemas.Pontuacao.competidor),
                joinedload(schemas.Pontuacao.prova),
                joinedload(schemas.Pontuacao.categoria)
            ).where(schemas.Pontuacao.id == pontuacao_id)
            
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self.get_by_id)

    async def get_by_competidor_prova(self, competidor_id: int, prova_id: int, categoria_id: int) -> Optional[schemas.Pontuacao]:
        """Recupera pontuação específica de um competidor em uma prova/categoria"""
        try:
            stmt = select(schemas.Pontuacao).options(
                joinedload(schemas.Pontuacao.competidor),
                joinedload(schemas.Pontuacao.prova),
                joinedload(schemas.Pontuacao.categoria)
            ).where(
                and_(
                    schemas.Pontuacao.competidor_id == competidor_id,
                    schemas.Pontuacao.prova_id == prova_id,
                    schemas.Pontuacao.categoria_id == categoria_id
                )
            )
            
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self.get_by_competidor_prova)

    async def get_by_competidor(self, competidor_id: int, ano: Optional[int] = None, categoria_id: Optional[int] = None) -> List[schemas.Pontuacao]:
        """Recupera todas as pontuações de um competidor"""
        try:
            stmt = select(schemas.Pontuacao).options(
                joinedload(schemas.Pontuacao.prova),
                joinedload(schemas.Pontuacao.categoria)
            ).where(schemas.Pontuacao.competidor_id == competidor_id)
            
            if ano:
                stmt = stmt.join(schemas.Provas).where(
                    extract('year', schemas.Provas.data) == ano
                )
            
            if categoria_id:
                stmt = stmt.where(schemas.Pontuacao.categoria_id == categoria_id)
            
            stmt = stmt.order_by(desc(schemas.Pontuacao.created_at))
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_by_competidor)

    async def get_by_prova(self, prova_id: int, categoria_id: Optional[int] = None) -> List[schemas.Pontuacao]:
        """Recupera pontuações de uma prova"""
        try:
            stmt = select(schemas.Pontuacao).options(
                joinedload(schemas.Pontuacao.competidor),
                joinedload(schemas.Pontuacao.categoria)
            ).where(schemas.Pontuacao.prova_id == prova_id)
            
            if categoria_id:
                stmt = stmt.where(schemas.Pontuacao.categoria_id == categoria_id)
            
            stmt = stmt.order_by(desc(schemas.Pontuacao.pontos_total))
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_by_prova)

    async def get_by_categoria(self, categoria_id: int, ano: Optional[int] = None, limite: Optional[int] = None) -> List[schemas.Pontuacao]:
        """Recupera pontuações de uma categoria"""
        try:
            stmt = select(schemas.Pontuacao).options(
                joinedload(schemas.Pontuacao.competidor),
                joinedload(schemas.Pontuacao.prova)
            ).where(schemas.Pontuacao.categoria_id == categoria_id)
            
            if ano:
                stmt = stmt.join(schemas.Provas).where(
                    extract('year', schemas.Provas.data) == ano
                )
            
            stmt = stmt.order_by(desc(schemas.Pontuacao.pontos_total))
            
            if limite:
                stmt = stmt.limit(limite)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_by_categoria)

    async def post(self, pontuacao_data: models.PontuacaoPOST) -> schemas.Pontuacao:
        """Cria uma nova pontuação"""
        try:
            # Verificar se já existe pontuação para este competidor/prova/categoria
            pontuacao_existente = await self.get_by_competidor_prova(
                pontuacao_data.competidor_id,
                pontuacao_data.prova_id,
                pontuacao_data.categoria_id
            )
            
            if pontuacao_existente:
                raise PontuacaoException("Já existe pontuação para este competidor nesta prova/categoria")

            db_pontuacao = schemas.Pontuacao(
                competidor_id=pontuacao_data.competidor_id,
                prova_id=pontuacao_data.prova_id,
                categoria_id=pontuacao_data.categoria_id,
                pontos_colocacao=pontuacao_data.pontos_colocacao,
                pontos_premiacao=pontuacao_data.pontos_premiacao,
                pontos_total=pontuacao_data.pontos_total,
                colocacao=pontuacao_data.colocacao,
                premiacao_valor=pontuacao_data.premiacao_valor
            )

            # Calcular campos derivados
            db_pontuacao.calcular_pontos_colocacao()
            db_pontuacao.calcular_pontos_premiacao()
            db_pontuacao.calcular_pontos_total()

            self.db.add(db_pontuacao)
            self.db.commit()
            self.db.refresh(db_pontuacao)
            
            return db_pontuacao
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.post)

    async def put(self, pontuacao_id: int, pontuacao_data: models.PontuacaoPUT) -> Optional[schemas.Pontuacao]:
        """Atualiza uma pontuação"""
        try:
            pontuacao_existente = await self.get_by_id(pontuacao_id)
            if not pontuacao_existente:
                raise PontuacaoException(f"Pontuação com ID {pontuacao_id} não encontrada")

            # Criar dicionário apenas com campos não None
            update_data = {k: v for k, v in pontuacao_data.model_dump().items() if v is not None}
            
            if update_data:
                stmt = update(schemas.Pontuacao).where(
                    schemas.Pontuacao.id == pontuacao_id
                ).values(**update_data)
                
                self.db.execute(stmt)
                
                # Recalcular campos derivados
                pontuacao_atualizada = await self.get_by_id(pontuacao_id)
                pontuacao_atualizada.calcular_pontos_colocacao()
                pontuacao_atualizada.calcular_pontos_premiacao()
                pontuacao_atualizada.calcular_pontos_total()
                
                self.db.commit()
            
            return await self.get_by_id(pontuacao_id)
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.put)

    async def delete(self, pontuacao_id: int) -> bool:
        """Remove uma pontuação"""
        try:
            pontuacao = await self.get_by_id(pontuacao_id)
            if not pontuacao:
                raise PontuacaoException(f"Pontuação com ID {pontuacao_id} não encontrada")

            stmt = delete(schemas.Pontuacao).where(
                schemas.Pontuacao.id == pontuacao_id
            )
            
            self.db.execute(stmt)
            self.db.commit()
            return True
                
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.delete)

    # ---------------------- Cálculos Automáticos ----------------------

    async def calcular_pontuacao_resultado(self, resultado: schemas.Resultados) -> Dict[str, Any]:
        """Calcula pontuação baseada em um resultado e cria/atualiza registros"""
        try:
            # Buscar trio com integrantes
            trio = self.db.execute(
                select(schemas.Trios).options(
                    joinedload(schemas.Trios.integrantes).joinedload(schemas.IntegrantesTrios.competidor)
                ).where(schemas.Trios.id == resultado.trio_id)
            ).scalars().first()

            if not trio:
                raise PontuacaoException("Trio não encontrado para o resultado")

            pontuacoes_criadas = []
            pontuacoes_atualizadas = []

            # Calcular pontos
            pontos_colocacao = UtilsLCTP.calcular_pontos_colocacao(resultado.colocacao or 0)
            
            # Dividir premiação entre os 3 integrantes
            premiacao_individual = float(resultado.premiacao_liquida or 0) / 3
            pontos_premiacao = UtilsLCTP.calcular_pontos_premiacao(premiacao_individual)
            pontos_total = pontos_colocacao + pontos_premiacao

            # Criar/atualizar pontuação para cada integrante
            for integrante in trio.integrantes:
                pontuacao_existente = await self.get_by_competidor_prova(
                    integrante.competidor_id,
                    resultado.prova_id,
                    trio.categoria_id
                )

                dados_pontuacao = {
                    'pontos_colocacao': pontos_colocacao,
                    'pontos_premiacao': pontos_premiacao,
                    'pontos_total': pontos_total,
                    'colocacao': resultado.colocacao,
                    'premiacao_valor': Decimal(str(premiacao_individual))
                }

                if pontuacao_existente:
                    # Atualizar existente
                    pontuacao_put = models.PontuacaoPUT(**dados_pontuacao)
                    pontuacao = await self.put(pontuacao_existente.id, pontuacao_put)
                    pontuacoes_atualizadas.append(pontuacao)
                else:
                    # Criar nova
                    pontuacao_post = models.PontuacaoPOST(
                        competidor_id=integrante.competidor_id,
                        prova_id=resultado.prova_id,
                        categoria_id=trio.categoria_id,
                        **dados_pontuacao
                    )
                    pontuacao = await self.post(pontuacao_post)
                    pontuacoes_criadas.append(pontuacao)

            return {
                'pontuacoes_criadas': len(pontuacoes_criadas),
                'pontuacoes_atualizadas': len(pontuacoes_atualizadas),
                'pontos_colocacao': pontos_colocacao,
                'pontos_premiacao': pontos_premiacao,
                'pontos_total': pontos_total,
                'premiacao_individual': premiacao_individual
            }

        except Exception as error:
            self.db.rollback()
            handle_error(error, self.calcular_pontuacao_resultado)

    async def recalcular_pontuacao_prova(self, prova_id: int) -> Dict[str, Any]:
        """Recalcula toda a pontuação de uma prova"""
        try:
            # Buscar resultados da prova
            resultados = self.db.execute(
                select(schemas.Resultados).where(
                    schemas.Resultados.prova_id == prova_id
                )
            ).scalars().all()

            if not resultados:
                raise PontuacaoException("Nenhum resultado encontrado para esta prova")

            # Remover pontuações existentes da prova
            self.db.execute(
                delete(schemas.Pontuacao).where(
                    schemas.Pontuacao.prova_id == prova_id
                )
            )

            total_criadas = 0
            total_atualizadas = 0

            # Recalcular para cada resultado
            for resultado in resultados:
                calculo = await self.calcular_pontuacao_resultado(resultado)
                total_criadas += calculo['pontuacoes_criadas']
                total_atualizadas += calculo['pontuacoes_atualizadas']

            return {
                'prova_id': prova_id,
                'resultados_processados': len(resultados),
                'pontuacoes_criadas': total_criadas,
                'pontuacoes_atualizadas': total_atualizadas,
                'sucesso': True
            }

        except Exception as error:
            self.db.rollback()
            handle_error(error, self.recalcular_pontuacao_prova)

    # ---------------------- Rankings e Estatísticas ----------------------

    async def get_ranking_geral(self, ano: Optional[int] = None, categoria_id: Optional[int] = None, limite: int = 50) -> List[Dict[str, Any]]:
        """Gera ranking geral de competidores"""
        try:
            # Query base
            stmt = select(
                schemas.Pontuacao.competidor_id,
                schemas.Competidores.nome,
                schemas.Competidores.handicap,
                schemas.Competidores.cidade,
                schemas.Competidores.estado,
                func.sum(schemas.Pontuacao.pontos_total).label('total_pontos'),
                func.count(schemas.Pontuacao.id).label('total_provas'),
                func.avg(schemas.Pontuacao.pontos_total).label('media_pontos'),
                func.min(schemas.Pontuacao.colocacao).label('melhor_colocacao'),
                func.sum(schemas.Pontuacao.premiacao_valor).label('premiacao_total')
            ).join(
                schemas.Competidores,
                schemas.Pontuacao.competidor_id == schemas.Competidores.id
            )

            if ano:
                stmt = stmt.join(schemas.Provas).where(
                    extract('year', schemas.Provas.data) == ano
                )

            if categoria_id:
                stmt = stmt.where(schemas.Pontuacao.categoria_id == categoria_id)

            stmt = stmt.group_by(
                schemas.Pontuacao.competidor_id,
                schemas.Competidores.nome,
                schemas.Competidores.handicap,
                schemas.Competidores.cidade,
                schemas.Competidores.estado
            ).order_by(
                desc('total_pontos')
            ).limit(limite)

            resultados = self.db.execute(stmt).all()

            ranking = []
            for i, resultado in enumerate(resultados, 1):
                ranking.append({
                    'posicao': i,
                    'competidor_id': resultado.competidor_id,
                    'nome': resultado.nome,
                    'handicap': resultado.handicap,
                    'cidade': resultado.cidade,
                    'estado': resultado.estado,
                    'total_pontos': float(resultado.total_pontos or 0),
                    'total_provas': resultado.total_provas,
                    'media_pontos': round(float(resultado.media_pontos or 0), 2),
                    'melhor_colocacao': resultado.melhor_colocacao,
                    'premiacao_total': float(resultado.premiacao_total or 0)
                })

            return ranking

        except Exception as error:
            handle_error(error, self.get_ranking_geral)

    async def get_ranking_categoria(self, categoria_id: int, ano: Optional[int] = None, limite: int = 30) -> List[Dict[str, Any]]:
        """Gera ranking específico de uma categoria"""
        try:
            return await self.get_ranking_geral(ano, categoria_id, limite)
        except Exception as error:
            handle_error(error, self.get_ranking_categoria)

    async def get_estatisticas_competidor(self, competidor_id: int, ano: Optional[int] = None) -> Dict[str, Any]:
        """Gera estatísticas detalhadas de um competidor"""
        try:
            pontuacoes = await self.get_by_competidor(competidor_id, ano)

            if not pontuacoes:
                return {
                    'competidor_id': competidor_id,
                    'ano': ano,
                    'total_provas': 0,
                    'total_pontos': 0,
                    'media_pontos': 0,
                    'melhor_colocacao': None,
                    'pior_colocacao': None,
                    'premiacao_total': 0,
                    'por_categoria': {}
                }

            # Estatísticas gerais
            total_pontos = sum(p.pontos_total for p in pontuacoes)
            total_provas = len(pontuacoes)
            media_pontos = total_pontos / total_provas if total_provas > 0 else 0
            
            colocacoes = [p.colocacao for p in pontuacoes if p.colocacao]
            melhor_colocacao = min(colocacoes) if colocacoes else None
            pior_colocacao = max(colocacoes) if colocacoes else None
            
            premiacao_total = sum(float(p.premiacao_valor or 0) for p in pontuacoes)

            # Estatísticas por categoria
            por_categoria = {}
            for pontuacao in pontuacoes:
                categoria_nome = pontuacao.categoria.nome
                if categoria_nome not in por_categoria:
                    por_categoria[categoria_nome] = {
                        'total_provas': 0,
                        'total_pontos': 0,
                        'media_pontos': 0,
                        'melhor_colocacao': None,
                        'premiacao_total': 0
                    }

                cat_stats = por_categoria[categoria_nome]
                cat_stats['total_provas'] += 1
                cat_stats['total_pontos'] += pontuacao.pontos_total
                cat_stats['premiacao_total'] += float(pontuacao.premiacao_valor or 0)

                if pontuacao.colocacao:
                    if not cat_stats['melhor_colocacao'] or pontuacao.colocacao < cat_stats['melhor_colocacao']:
                        cat_stats['melhor_colocacao'] = pontuacao.colocacao

            # Calcular médias por categoria
            for categoria in por_categoria.values():
                if categoria['total_provas'] > 0:
                    categoria['media_pontos'] = round(categoria['total_pontos'] / categoria['total_provas'], 2)

            # Evolução temporal (últimas 10 provas)
            pontuacoes_recentes = pontuacoes[:10]
            evolucao = []
            for pontuacao in pontuacoes_recentes:
                evolucao.append({
                    'data': pontuacao.prova.data.isoformat(),
                    'prova_nome': pontuacao.prova.nome,
                    'categoria': pontuacao.categoria.nome,
                    'pontos': pontuacao.pontos_total,
                    'colocacao': pontuacao.colocacao
                })

            return {
                'competidor_id': competidor_id,
                'competidor_nome': pontuacoes[0].competidor.nome if pontuacoes else None,
                'ano': ano,
                'total_provas': total_provas,
                'total_pontos': round(total_pontos, 2),
                'media_pontos': round(media_pontos, 2),
                'melhor_colocacao': melhor_colocacao,
                'pior_colocacao': pior_colocacao,
                'premiacao_total': round(premiacao_total, 2),
                'por_categoria': por_categoria,
                'evolucao_recente': evolucao
            }

        except Exception as error:
            handle_error(error, self.get_estatisticas_competidor)

    # ---------------------- Relatórios e Análises ----------------------

    async def gerar_relatorio_pontuacao_ano(self, ano: int) -> Dict[str, Any]:
        """Gera relatório completo de pontuação do ano"""
        try:
            # Buscar todas as pontuações do ano
            pontuacoes = self.db.execute(
                select(schemas.Pontuacao).options(
                    joinedload(schemas.Pontuacao.competidor),
                    joinedload(schemas.Pontuacao.prova),
                    joinedload(schemas.Pontuacao.categoria)
                ).join(
                    schemas.Provas
                ).where(
                    extract('year', schemas.Provas.data) == ano
                )
            ).scalars().all()

            if not pontuacoes:
                return {
                    'ano': ano,
                    'total_pontuacoes': 0,
                    'total_competidores': 0,
                    'total_provas': 0,
                    'por_categoria': {},
                    'campeoes': {}
                }

            # Estatísticas gerais
            total_pontuacoes = len(pontuacoes)
            competidores_unicos = len(set(p.competidor_id for p in pontuacoes))
            provas_unicas = len(set(p.prova_id for p in pontuacoes))
            pontos_totais = sum(p.pontos_total for p in pontuacoes)
            premiacao_total = sum(float(p.premiacao_valor or 0) for p in pontuacoes)

            # Análise por categoria
            por_categoria = {}
            for pontuacao in pontuacoes:
                categoria_nome = pontuacao.categoria.nome
                if categoria_nome not in por_categoria:
                    por_categoria[categoria_nome] = {
                        'total_pontuacoes': 0,
                        'competidores_unicos': set(),
                        'total_pontos': 0,
                        'premiacao_total': 0,
                        'media_pontos': 0
                    }

                cat_stats = por_categoria[categoria_nome]
                cat_stats['total_pontuacoes'] += 1
                cat_stats['competidores_unicos'].add(pontuacao.competidor_id)
                cat_stats['total_pontos'] += pontuacao.pontos_total
                cat_stats['premiacao_total'] += float(pontuacao.premiacao_valor or 0)

            # Converter sets para counts e calcular médias
            for categoria in por_categoria.values():
                categoria['competidores_unicos'] = len(categoria['competidores_unicos'])
                if categoria['total_pontuacoes'] > 0:
                    categoria['media_pontos'] = round(categoria['total_pontos'] / categoria['total_pontuacoes'], 2)

            # Campeões por categoria (top 3)
            campeoes = {}
            for categoria_nome in por_categoria.keys():
                categoria = self.db.execute(
                    select(schemas.Categorias).where(
                        schemas.Categorias.nome == categoria_nome
                    )
                ).scalars().first()
                
                if categoria:
                    ranking_categoria = await self.get_ranking_categoria(categoria.id, ano, 3)
                    campeoes[categoria_nome] = ranking_categoria

            relatorio = {
                'ano': ano,
                'resumo_geral': {
                    'total_pontuacoes': total_pontuacoes,
                    'total_competidores': competidores_unicos,
                    'total_provas': provas_unicas,
                    'pontos_totais_distribuidos': round(pontos_totais, 2),
                    'premiacao_total_distribuida': round(premiacao_total, 2),
                    'media_pontos_por_participacao': round(pontos_totais / total_pontuacoes, 2) if total_pontuacoes > 0 else 0
                },
                'por_categoria': por_categoria,
                'campeoes_por_categoria': campeoes,
                'gerado_em': datetime.now(timezone.utc).astimezone(AMSP).isoformat()
            }

            return relatorio

        except Exception as error:
            handle_error(error, self.gerar_relatorio_pontuacao_ano)

    # ---------------------- Exportação e Importação ----------------------

    async def exportar_pontuacoes(self, filtros: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Exporta pontuações em formato estruturado"""
        try:
            stmt = select(schemas.Pontuacao).options(
                joinedload(schemas.Pontuacao.competidor),
                joinedload(schemas.Pontuacao.prova),
                joinedload(schemas.Pontuacao.categoria)
            )

            # Aplicar filtros se fornecidos
            if filtros:
                if 'ano' in filtros:
                    stmt = stmt.join(schemas.Provas).where(
                        extract('year', schemas.Provas.data) == filtros['ano']
                    )
                
                if 'categoria_id' in filtros:
                    stmt = stmt.where(schemas.Pontuacao.categoria_id == filtros['categoria_id'])
                
                if 'competidor_id' in filtros:
                    stmt = stmt.where(schemas.Pontuacao.competidor_id == filtros['competidor_id'])

            stmt = stmt.order_by(desc(schemas.Pontuacao.created_at))

            pontuacoes = self.db.execute(stmt).scalars().all()

            export_data = []
            for pontuacao in pontuacoes:
                export_data.append({
                    'id': pontuacao.id,
                    'competidor_id': pontuacao.competidor_id,
                    'competidor_nome': pontuacao.competidor.nome,
                    'competidor_handicap': pontuacao.competidor.handicap,
                    'prova_id': pontuacao.prova_id,
                    'prova_nome': pontuacao.prova.nome,
                    'prova_data': pontuacao.prova.data.isoformat(),
                    'categoria_id': pontuacao.categoria_id,
                    'categoria_nome': pontuacao.categoria.nome,
                    'pontos_colocacao': pontuacao.pontos_colocacao,
                    'pontos_premiacao': pontuacao.pontos_premiacao,
                    'pontos_total': pontuacao.pontos_total,
                    'colocacao': pontuacao.colocacao,
                    'premiacao_valor': float(pontuacao.premiacao_valor or 0),
                    'created_at': pontuacao.created_at.isoformat() if pontuacao.created_at else None
                })

            return export_data

        except Exception as error:
            handle_error(error, self.exportar_pontuacoes)

    # ---------------------- Validações e Utilitários ----------------------

    async def validar_consistencia_pontuacao(self, prova_id: Optional[int] = None) -> Dict[str, Any]:
        """Valida consistência dos dados de pontuação"""
        try:
            query = self.db.query(schemas.Pontuacao).options(
                joinedload(schemas.Pontuacao.competidor),
                joinedload(schemas.Pontuacao.prova)
            )

            if prova_id:
                query = query.filter(schemas.Pontuacao.prova_id == prova_id)

            pontuacoes = query.all()

            inconsistencias = []
            
            for pontuacao in pontuacoes:
                # Verificar se pontos totais estão corretos
                pontos_esperados = pontuacao.pontos_colocacao + pontuacao.pontos_premiacao
                if abs(pontuacao.pontos_total - pontos_esperados) > 0.01:
                    inconsistencias.append(
                        f"Pontuação total incorreta para {pontuacao.competidor.nome} na prova {pontuacao.prova.nome}: "
                        f"esperado {pontos_esperados}, atual {pontuacao.pontos_total}"
                    )

                # Verificar pontos de colocação
                if pontuacao.colocacao:
                    pontos_colocacao_esperados = UtilsLCTP.calcular_pontos_colocacao(pontuacao.colocacao)
                    if abs(pontuacao.pontos_colocacao - pontos_colocacao_esperados) > 0.01:
                        inconsistencias.append(
                            f"Pontos de colocação incorretos para {pontuacao.competidor.nome}: "
                            f"colocação {pontuacao.colocacao}, esperado {pontos_colocacao_esperados}, atual {pontuacao.pontos_colocacao}"
                        )

                # Verificar pontos de premiação
                if pontuacao.premiacao_valor:
                    pontos_premiacao_esperados = UtilsLCTP.calcular_pontos_premiacao(float(pontuacao.premiacao_valor))
                    if abs(pontuacao.pontos_premiacao - pontos_premiacao_esperados) > 0.01:
                        inconsistencias.append(
                            f"Pontos de premiação incorretos para {pontuacao.competidor.nome}: "
                            f"premiação R${pontuacao.premiacao_valor}, esperado {pontos_premiacao_esperados}, atual {pontuacao.pontos_premiacao}"
                        )

                # Verificar se colocação está dentro dos limites
                if pontuacao.colocacao and pontuacao.colocacao < 1:
                    inconsistencias.append(
                        f"Colocação inválida para {pontuacao.competidor.nome}: {pontuacao.colocacao}"
                    )

                # Verificar valores negativos
                if pontuacao.pontos_total < 0 or pontuacao.pontos_colocacao < 0 or pontuacao.pontos_premiacao < 0:
                    inconsistencias.append(
                        f"Valores negativos encontrados para {pontuacao.competidor.nome} na prova {pontuacao.prova.nome}"
                    )

            return {
                'prova_id': prova_id,
                'total_pontuacoes': len(pontuacoes),
                'total_inconsistencias': len(inconsistencias),
                'inconsistencias': inconsistencias,
                'valido': len(inconsistencias) == 0
            }

        except Exception as error:
            handle_error(error, self.validar_consistencia_pontuacao)

    async def recalcular_todos_pontos(self, pontuacao_id: int) -> bool:
        """Recalcula todos os pontos de uma pontuação específica"""
        try:
            pontuacao = await self.get_by_id(pontuacao_id)
            if not pontuacao:
                return False

            # Recalcular campos
            pontuacao.calcular_pontos_colocacao()
            pontuacao.calcular_pontos_premiacao()
            pontuacao.calcular_pontos_total()

            # Atualizar no banco
            stmt = update(schemas.Pontuacao).where(
                schemas.Pontuacao.id == pontuacao_id
            ).values(
                pontos_colocacao=pontuacao.pontos_colocacao,
                pontos_premiacao=pontuacao.pontos_premiacao,
                pontos_total=pontuacao.pontos_total
            )

            self.db.execute(stmt)
            self.db.commit()
            return True

        except Exception as error:
            self.db.rollback()
            handle_error(error, self.recalcular_todos_pontos)

    async def get_competidores_com_mais_pontos(self, categoria_id: Optional[int] = None, ano: Optional[int] = None, limite: int = 10) -> List[Dict[str, Any]]:
        """Retorna competidores com mais pontos no período"""
        try:
            ranking = await self.get_ranking_geral(ano, categoria_id, limite)
            return ranking

        except Exception as error:
            handle_error(error, self.get_competidores_com_mais_pontos)

    async def get_historico_competidor_categoria(self, competidor_id: int, categoria_id: int) -> Dict[str, Any]:
        """Retorna histórico completo de um competidor em uma categoria"""
        try:
            pontuacoes = self.db.execute(
                select(schemas.Pontuacao).options(
                    joinedload(schemas.Pontuacao.prova)
                ).where(
                    and_(
                        schemas.Pontuacao.competidor_id == competidor_id,
                        schemas.Pontuacao.categoria_id == categoria_id
                    )
                ).order_by(schemas.Pontuacao.created_at)
            ).scalars().all()

            if not pontuacoes:
                return {
                    'competidor_id': competidor_id,
                    'categoria_id': categoria_id,
                    'total_participacoes': 0,
                    'historico': []
                }

            historico = []
            pontos_acumulados = 0
            
            for pontuacao in pontuacoes:
                pontos_acumulados += pontuacao.pontos_total
                
                historico.append({
                    'prova_nome': pontuacao.prova.nome,
                    'prova_data': pontuacao.prova.data.isoformat(),
                    'colocacao': pontuacao.colocacao,
                    'pontos_prova': pontuacao.pontos_total,
                    'pontos_acumulados': round(pontos_acumulados, 2),
                    'premiacao': float(pontuacao.premiacao_valor or 0)
                })

            # Estatísticas do histórico
            colocacoes = [p.colocacao for p in pontuacoes if p.colocacao]
            premiacoes = [float(p.premiacao_valor or 0) for p in pontuacoes if p.premiacao_valor]

            estatisticas = {
                'total_participacoes': len(pontuacoes),
                'total_pontos': round(pontos_acumulados, 2),
                'media_pontos': round(pontos_acumulados / len(pontuacoes), 2),
                'melhor_colocacao': min(colocacoes) if colocacoes else None,
                'pior_colocacao': max(colocacoes) if colocacoes else None,
                'total_premiacoes': round(sum(premiacoes), 2),
                'media_premiacao': round(sum(premiacoes) / len(premiacoes), 2) if premiacoes else 0,
                'participacoes_premiadas': len(premiacoes)
            }

            return {
                'competidor_id': competidor_id,
                'categoria_id': categoria_id,
                'estatisticas': estatisticas,
                'historico': historico
            }

        except Exception as error:
            handle_error(error, self.get_historico_competidor_categoria)

    async def get_media_pontos_categoria(self, categoria_id: int, ano: Optional[int] = None) -> Dict[str, Any]:
        """Calcula médias de pontuação de uma categoria"""
        try:
            stmt = select(
                func.avg(schemas.Pontuacao.pontos_total).label('media_pontos_total'),
                func.avg(schemas.Pontuacao.pontos_colocacao).label('media_pontos_colocacao'),
                func.avg(schemas.Pontuacao.pontos_premiacao).label('media_pontos_premiacao'),
                func.count(schemas.Pontuacao.id).label('total_pontuacoes'),
                func.count(func.distinct(schemas.Pontuacao.competidor_id)).label('competidores_unicos')
            ).where(schemas.Pontuacao.categoria_id == categoria_id)

            if ano:
                stmt = stmt.join(schemas.Provas).where(
                    extract('year', schemas.Provas.data) == ano
                )

            resultado = self.db.execute(stmt).first()

            if not resultado or resultado.total_pontuacoes == 0:
                return {
                    'categoria_id': categoria_id,
                    'ano': ano,
                    'sem_dados': True
                }

            return {
                'categoria_id': categoria_id,
                'ano': ano,
                'media_pontos_total': round(float(resultado.media_pontos_total or 0), 2),
                'media_pontos_colocacao': round(float(resultado.media_pontos_colocacao or 0), 2),
                'media_pontos_premiacao': round(float(resultado.media_pontos_premiacao or 0), 2),
                'total_pontuacoes': resultado.total_pontuacoes,
                'competidores_unicos': resultado.competidores_unicos
            }

        except Exception as error:
            handle_error(error, self.get_media_pontos_categoria)