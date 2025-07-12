from sqlalchemy import select, delete, update, func, desc, asc, and_, or_, case
from sqlalchemy.orm import Session, joinedload
from src.database import models, schemas
from src.utils.error_handler import handle_error
from src.utils.utils_lctp import UtilsLCTP
from src.utils.config_lctp import ConfigLCTP
from src.utils.exceptions_lctp import PontuacaoException, LCTPException
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
import pytz

AMSP = pytz.timezone('America/Sao_Paulo')

class RepositorioResultado:
    """Repositório para operações com resultados e pontuação do sistema LCTP"""
    
    def __init__(self, db: Session):
        self.db = db

    # ---------------------- Operações Básicas ----------------------

    async def get_by_id(self, resultado_id: int) -> Optional[schemas.Resultados]:
        """Recupera um resultado pelo ID"""
        try:
            stmt = select(schemas.Resultados).options(
                joinedload(schemas.Resultados.trio).joinedload(schemas.Trios.integrantes).joinedload(schemas.IntegrantesTrios.competidor),
                joinedload(schemas.Resultados.trio).joinedload(schemas.Trios.categoria),
                joinedload(schemas.Resultados.prova)
            ).where(schemas.Resultados.id == resultado_id)
            
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self.get_by_id)

    async def get_by_trio(self, trio_id: int) -> Optional[schemas.Resultados]:
        """Recupera resultado de um trio"""
        try:
            stmt = select(schemas.Resultados).options(
                joinedload(schemas.Resultados.trio),
                joinedload(schemas.Resultados.prova)
            ).where(schemas.Resultados.trio_id == trio_id)
            
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self.get_by_trio)

    async def get_by_prova(self, prova_id: int, categoria_id: Optional[int] = None) -> List[schemas.Resultados]:
        """Recupera resultados de uma prova (opcionalmente filtrados por categoria)"""
        try:
            stmt = select(schemas.Resultados).options(
                joinedload(schemas.Resultados.trio).joinedload(schemas.Trios.integrantes).joinedload(schemas.IntegrantesTrios.competidor),
                joinedload(schemas.Resultados.trio).joinedload(schemas.Trios.categoria)
            ).where(schemas.Resultados.prova_id == prova_id)

            if categoria_id:
                stmt = stmt.join(schemas.Trios).where(schemas.Trios.categoria_id == categoria_id)

            stmt = stmt.order_by(schemas.Resultados.colocacao.asc())
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_by_prova)

    async def post(self, resultado_data: models.ResultadoPOST) -> schemas.Resultados:
        """Cria um novo resultado"""
        try:
            # Verificar se o trio existe
            trio = self.db.execute(
                select(schemas.Trios).where(schemas.Trios.id == resultado_data.trio_id)
            ).scalars().first()
            
            if not trio:
                raise LCTPException("Trio não encontrado")

            # Verificar se já existe resultado para este trio
            resultado_existente = await self.get_by_trio(resultado_data.trio_id)
            if resultado_existente:
                raise LCTPException("Trio já possui resultado cadastrado")

            db_resultado = schemas.Resultados(
                trio_id=resultado_data.trio_id,
                prova_id=resultado_data.prova_id,
                passada1_tempo=resultado_data.passada1_tempo,
                passada2_tempo=resultado_data.passada2_tempo,
                colocacao=resultado_data.colocacao,
                premiacao_valor=resultado_data.premiacao_valor,
                no_time=resultado_data.no_time,
                desclassificado=resultado_data.desclassificado,
                observacoes=resultado_data.observacoes
            )

            # Calcular campos derivados
            db_resultado.calcular_media()
            db_resultado.calcular_premiacao_liquida()

            self.db.add(db_resultado)
            self.db.commit()
            self.db.refresh(db_resultado)
            
            return db_resultado
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.post)

    async def put(self, resultado_id: int, resultado_data: models.ResultadoPUT) -> Optional[schemas.Resultados]:
        """Atualiza um resultado"""
        try:
            resultado_existente = await self.get_by_id(resultado_id)
            if not resultado_existente:
                raise LCTPException(f"Resultado com ID {resultado_id} não encontrado")

            # Criar dicionário apenas com campos não None
            update_data = {k: v for k, v in resultado_data.model_dump().items() if v is not None}
            
            if update_data:
                stmt = update(schemas.Resultados).where(
                    schemas.Resultados.id == resultado_id
                ).values(**update_data)
                
                self.db.execute(stmt)
                
                # Recalcular campos derivados
                resultado_atualizado = await self.get_by_id(resultado_id)
                resultado_atualizado.calcular_media()
                resultado_atualizado.calcular_premiacao_liquida()
                
                self.db.commit()
            
            return await self.get_by_id(resultado_id)
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.put)

    async def delete(self, resultado_id: int) -> bool:
        """Remove um resultado"""
        try:
            resultado = await self.get_by_id(resultado_id)
            if not resultado:
                raise LCTPException(f"Resultado com ID {resultado_id} não encontrado")

            # Remover pontuações associadas primeiro
            self.db.execute(
                delete(schemas.Pontuacao).where(
                    and_(
                        schemas.Pontuacao.prova_id == resultado.prova_id,
                        schemas.Pontuacao.competidor_id.in_(
                            select(schemas.IntegrantesTrios.competidor_id).where(
                                schemas.IntegrantesTrios.trio_id == resultado.trio_id
                            )
                        )
                    )
                )
            )

            # Remover resultado
            stmt = delete(schemas.Resultados).where(
                schemas.Resultados.id == resultado_id
            )
            
            self.db.execute(stmt)
            self.db.commit()
            return True
                
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.delete)

    # ---------------------- Lançamento de Resultados em Lote ----------------------

    async def lancar_resultados_prova(self, prova_id: int, resultados_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Lança resultados de uma prova completa"""
        try:
            resultados_criados = []
            resultados_atualizados = []
            erros = []

            for resultado_info in resultados_data:
                try:
                    trio_id = resultado_info.get('trio_id')
                    if not trio_id:
                        erros.append("trio_id é obrigatório")
                        continue

                    # Verificar se já existe resultado
                    resultado_existente = await self.get_by_trio(trio_id)
                    
                    resultado_data = models.ResultadoPOST(
                        trio_id=trio_id,
                        prova_id=prova_id,
                        passada1_tempo=resultado_info.get('passada1_tempo'),
                        passada2_tempo=resultado_info.get('passada2_tempo'),
                        colocacao=resultado_info.get('colocacao'),
                        premiacao_valor=resultado_info.get('premiacao_valor'),
                        no_time=resultado_info.get('no_time', False),
                        desclassificado=resultado_info.get('desclassificado', False),
                        observacoes=resultado_info.get('observacoes')
                    )

                    if resultado_existente:
                        # Atualizar
                        resultado_put = models.ResultadoPUT(**resultado_data.model_dump())
                        resultado = await self.put(resultado_existente.id, resultado_put)
                        resultados_atualizados.append(resultado)
                    else:
                        # Criar novo
                        resultado = await self.post(resultado_data)
                        resultados_criados.append(resultado)

                except Exception as e:
                    erros.append(f"Erro no trio {trio_id}: {str(e)}")

            return {
                'resultados_criados': len(resultados_criados),
                'resultados_atualizados': len(resultados_atualizados),
                'erros': erros,
                'sucesso': len(erros) == 0
            }
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.lancar_resultados_prova)

    async def calcular_colocacoes_automaticas(self, prova_id: int, categoria_id: Optional[int] = None) -> bool:
        """Calcula colocações automaticamente baseado nos tempos médios"""
        try:
            # Buscar resultados da prova/categoria
            query = self.db.query(schemas.Resultados).join(
                schemas.Trios
            ).filter(
                schemas.Resultados.prova_id == prova_id,
                schemas.Resultados.media_tempo.isnot(None),
                schemas.Resultados.no_time == False,
                schemas.Resultados.desclassificado == False
            )

            if categoria_id:
                query = query.filter(schemas.Trios.categoria_id == categoria_id)

            # Ordenar por tempo médio
            resultados = query.order_by(schemas.Resultados.media_tempo.asc()).all()

            # Atribuir colocações
            for i, resultado in enumerate(resultados, 1):
                stmt = update(schemas.Resultados).where(
                    schemas.Resultados.id == resultado.id
                ).values(colocacao=i)
                
                self.db.execute(stmt)

            self.db.commit()
            return True
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.calcular_colocacoes_automaticas)

    # ---------------------- Pontuação CONTEP ----------------------

    async def calcular_pontuacao_contep(self, prova_id: int, categoria_id: Optional[int] = None) -> Dict[str, Any]:
        """Calcula pontuação CONTEP para uma prova/categoria"""
        try:
            # Buscar resultados
            resultados = await self.get_by_prova(prova_id, categoria_id)
            
            pontuacoes_criadas = 0
            pontuacoes_atualizadas = 0
            
            for resultado in resultados:
                # Para cada integrante do trio
                for integrante in resultado.trio.integrantes:
                    # Verificar se já existe pontuação
                    pontuacao_existente = self.db.execute(
                        select(schemas.Pontuacao).where(
                            and_(
                                schemas.Pontuacao.competidor_id == integrante.competidor_id,
                                schemas.Pontuacao.prova_id == prova_id,
                                schemas.Pontuacao.categoria_id == resultado.trio.categoria_id
                            )
                        )
                    ).scalars().first()

                    # Calcular pontos
                    pontos_colocacao = UtilsLCTP.calcular_pontos_colocacao(resultado.colocacao or 0)
                    pontos_premiacao = UtilsLCTP.calcular_pontos_premiacao(
                        float(resultado.premiacao_liquida or 0) / 3  # Dividir entre os 3 integrantes
                    )
                    pontos_total = pontos_colocacao + pontos_premiacao

                    if pontuacao_existente:
                        # Atualizar
                        stmt = update(schemas.Pontuacao).where(
                            schemas.Pontuacao.id == pontuacao_existente.id
                        ).values(
                            pontos_colocacao=pontos_colocacao,
                            pontos_premiacao=pontos_premiacao,
                            pontos_total=pontos_total,
                            colocacao=resultado.colocacao,
                            premiacao_valor=float(resultado.premiacao_liquida or 0) / 3
                        )
                        self.db.execute(stmt)
                        pontuacoes_atualizadas += 1
                    else:
                        # Criar nova
                        nova_pontuacao = schemas.Pontuacao(
                            competidor_id=integrante.competidor_id,
                            prova_id=prova_id,
                            categoria_id=resultado.trio.categoria_id,
                            pontos_colocacao=pontos_colocacao,
                            pontos_premiacao=pontos_premiacao,
                            pontos_total=pontos_total,
                            colocacao=resultado.colocacao,
                            premiacao_valor=Decimal(str(float(resultado.premiacao_liquida or 0) / 3))
                        )
                        self.db.add(nova_pontuacao)
                        pontuacoes_criadas += 1

            self.db.commit()
            
            return {
                'pontuacoes_criadas': pontuacoes_criadas,
                'pontuacoes_atualizadas': pontuacoes_atualizadas,
                'total_processado': pontuacoes_criadas + pontuacoes_atualizadas
            }
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.calcular_pontuacao_contep)

    # ---------------------- Rankings e Estatísticas ----------------------

    async def get_ranking_prova_categoria(self, prova_id: int, categoria_id: int) -> List[Dict[str, Any]]:
        """Gera ranking detalhado de uma prova/categoria"""
        try:
            resultados = await self.get_by_prova(prova_id, categoria_id)
            
            ranking = []
            for resultado in resultados:
                integrantes_info = []
                for integrante in resultado.trio.integrantes:
                    comp = integrante.competidor
                    integrantes_info.append({
                        'id': comp.id,
                        'nome': comp.nome,
                        'handicap': comp.handicap,
                        'idade': comp.idade,
                        'cidade': comp.cidade,
                        'estado': comp.estado
                    })

                ranking_item = {
                    'colocacao': resultado.colocacao,
                    'trio_id': resultado.trio_id,
                    'trio_numero': resultado.trio.numero_trio,
                    'integrantes': integrantes_info,
                    'passada1_tempo': resultado.passada1_tempo,
                    'passada2_tempo': resultado.passada2_tempo,
                    'media_tempo': resultado.media_tempo,
                    'premiacao_bruta': float(resultado.premiacao_valor or 0),
                    'premiacao_liquida': float(resultado.premiacao_liquida or 0),
                    'handicap_total': resultado.trio.handicap_total,
                    'idade_total': resultado.trio.idade_total,
                    'no_time': resultado.no_time,
                    'desclassificado': resultado.desclassificado,
                    'observacoes': resultado.observacoes
                }
                ranking.append(ranking_item)

            return ranking
        except Exception as error:
            handle_error(error, self.get_ranking_prova_categoria)

    async def get_estatisticas_resultado_categoria(self, categoria_id: int, ano: Optional[int] = None) -> Dict[str, Any]:
        """Gera estatísticas de resultados por categoria"""
        try:
            query = self.db.query(schemas.Resultados).join(
                schemas.Trios
            ).filter(
                schemas.Trios.categoria_id == categoria_id
            )

            if ano:
                query = query.join(schemas.Provas).filter(
                    func.extract('year', schemas.Provas.data) == ano
                )

            resultados = query.all()

            if not resultados:
                return {}

            # Análise de tempos
            tempos_validos = [r.media_tempo for r in resultados if r.media_tempo and not r.no_time]
            
            # Análise de premiação
            premiacoes = [float(r.premiacao_valor or 0) for r in resultados if r.premiacao_valor]
            
            # Contadores
            total_resultados = len(resultados)
            no_time_count = len([r for r in resultados if r.no_time])
            desclassificados = len([r for r in resultados if r.desclassificado])

            estatisticas = {
                'categoria_id': categoria_id,
                'ano': ano,
                'total_resultados': total_resultados,
                'trios_classificados': total_resultados - no_time_count - desclassificados,
                'no_time': no_time_count,
                'desclassificados': desclassificados,
                'tempos': {
                    'media': round(sum(tempos_validos) / len(tempos_validos), 2) if tempos_validos else 0,
                    'melhor': round(min(tempos_validos), 2) if tempos_validos else 0,
                    'pior': round(max(tempos_validos), 2) if tempos_validos else 0,
                    'total_com_tempo': len(tempos_validos)
                },
                'premiacao': {
                    'total': round(sum(premiacoes), 2),
                    'media': round(sum(premiacoes) / len(premiacoes), 2) if premiacoes else 0,
                    'maior': round(max(premiacoes), 2) if premiacoes else 0,
                    'trios_premiados': len(premiacoes)
                }
            }

            return estatisticas
        except Exception as error:
            handle_error(error, self.get_estatisticas_resultado_categoria)

    async def get_melhores_tempos_categoria(self, categoria_id: int, limite: int = 10, ano: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retorna os melhores tempos de uma categoria"""
        try:
            query = self.db.query(schemas.Resultados).join(
                schemas.Trios
            ).options(
                joinedload(schemas.Resultados.trio).joinedload(schemas.Trios.integrantes).joinedload(schemas.IntegrantesTrios.competidor),
                joinedload(schemas.Resultados.prova)
            ).filter(
                schemas.Trios.categoria_id == categoria_id,
                schemas.Resultados.media_tempo.isnot(None),
                schemas.Resultados.no_time == False,
                schemas.Resultados.desclassificado == False
            )

            if ano:
                query = query.join(schemas.Provas).filter(
                    func.extract('year', schemas.Provas.data) == ano
                )

            # Ordenar por tempo médio crescente
            resultados = query.order_by(schemas.Resultados.media_tempo.asc()).limit(limite).all()

            melhores_tempos = []
            for i, resultado in enumerate(resultados, 1):
                integrantes = [
                    {
                        'nome': integrante.competidor.nome,
                        'handicap': integrante.competidor.handicap
                    }
                    for integrante in resultado.trio.integrantes
                ]

                tempo_info = {
                    'posicao': i,
                    'tempo_medio': resultado.media_tempo,
                    'passada1': resultado.passada1_tempo,
                    'passada2': resultado.passada2_tempo,
                    'trio_numero': resultado.trio.numero_trio,
                    'integrantes': integrantes,
                    'prova_nome': resultado.prova.nome,
                    'prova_data': resultado.prova.data.isoformat(),
                    'colocacao_prova': resultado.colocacao
                }
                melhores_tempos.append(tempo_info)

            return melhores_tempos
        except Exception as error:
            handle_error(error, self.get_melhores_tempos_categoria)

    # ---------------------- Relatórios Avançados ----------------------

    async def gerar_relatorio_performance_prova(self, prova_id: int) -> Dict[str, Any]:
        """Gera relatório completo de performance de uma prova"""
        try:
            # Buscar dados básicos da prova
            prova = self.db.execute(
                select(schemas.Provas).where(schemas.Provas.id == prova_id)
            ).scalars().first()

            if not prova:
                raise LCTPException("Prova não encontrada")

            resultados = await self.get_by_prova(prova_id)
            
            # Análise geral
            total_trios = len(resultados)
            trios_classificados = len([r for r in resultados if not r.no_time and not r.desclassificado])
            no_time = len([r for r in resultados if r.no_time])
            desclassificados = len([r for r in resultados if r.desclassificado])

            # Análise por categoria
            por_categoria = {}
            for resultado in resultados:
                categoria_nome = resultado.trio.categoria.nome
                if categoria_nome not in por_categoria:
                    por_categoria[categoria_nome] = {
                        'total_trios': 0,
                        'classificados': 0,
                        'no_time': 0,
                        'desclassificados': 0,
                        'tempos': [],
                        'premiacao_total': 0
                    }

                cat_stats = por_categoria[categoria_nome]
                cat_stats['total_trios'] += 1
                
                if resultado.no_time:
                    cat_stats['no_time'] += 1
                elif resultado.desclassificado:
                    cat_stats['desclassificados'] += 1
                else:
                    cat_stats['classificados'] += 1
                    if resultado.media_tempo:
                        cat_stats['tempos'].append(resultado.media_tempo)

                if resultado.premiacao_valor:
                    cat_stats['premiacao_total'] += float(resultado.premiacao_valor)

            # Calcular médias por categoria
            for categoria in por_categoria.values():
                if categoria['tempos']:
                    categoria['tempo_medio'] = round(sum(categoria['tempos']) / len(categoria['tempos']), 2)
                    categoria['melhor_tempo'] = round(min(categoria['tempos']), 2)
                else:
                    categoria['tempo_medio'] = None
                    categoria['melhor_tempo'] = None

            # Análise de tempos geral
            todos_tempos = [r.media_tempo for r in resultados if r.media_tempo and not r.no_time]
            
            # Análise de premiação
            premiacao_total = sum(float(r.premiacao_valor or 0) for r in resultados)

            relatorio = {
                'prova': {
                    'id': prova.id,
                    'nome': prova.nome,
                    'data': prova.data.isoformat(),
                    'rancho': prova.rancho,
                    'cidade': prova.cidade,
                    'estado': prova.estado
                },
                'resumo_geral': {
                    'total_trios': total_trios,
                    'total_competidores': total_trios * 3,
                    'trios_classificados': trios_classificados,
                    'no_time': no_time,
                    'desclassificados': desclassificados,
                    'taxa_classificacao': round((trios_classificados / total_trios) * 100, 1) if total_trios > 0 else 0
                },
                'analise_tempos': {
                    'tempo_medio_geral': round(sum(todos_tempos) / len(todos_tempos), 2) if todos_tempos else 0,
                    'melhor_tempo_geral': round(min(todos_tempos), 2) if todos_tempos else 0,
                    'pior_tempo_geral': round(max(todos_tempos), 2) if todos_tempos else 0,
                    'total_com_tempo': len(todos_tempos)
                },
                'premiacao': {
                    'total_distribuida': round(premiacao_total, 2),
                    'media_por_trio_premiado': round(premiacao_total / len([r for r in resultados if r.premiacao_valor]), 2) if any(r.premiacao_valor for r in resultados) else 0
                },
                'por_categoria': por_categoria,
                'gerado_em': datetime.now(timezone.utc).astimezone(AMSP).isoformat()
            }

            return relatorio
        except Exception as error:
            handle_error(error, self.gerar_relatorio_performance_prova)

    async def comparar_performance_categorias(self, prova_id: int) -> Dict[str, Any]:
        """Compara performance entre categorias de uma prova"""
        try:
            resultados = await self.get_by_prova(prova_id)
            
            # Agrupar por categoria
            categorias = {}
            for resultado in resultados:
                categoria_nome = resultado.trio.categoria.nome
                if categoria_nome not in categorias:
                    categorias[categoria_nome] = []
                categorias[categoria_nome].append(resultado)

            comparacao = {}
            for categoria_nome, resultados_cat in categorias.items():
                # Análise da categoria
                tempos_validos = [r.media_tempo for r in resultados_cat if r.media_tempo and not r.no_time]
                
                comparacao[categoria_nome] = {
                    'total_trios': len(resultados_cat),
                    'trios_com_tempo': len(tempos_validos),
                    'taxa_conclusao': round((len(tempos_validos) / len(resultados_cat)) * 100, 1) if resultados_cat else 0,
                    'tempo_medio': round(sum(tempos_validos) / len(tempos_validos), 2) if tempos_validos else 0,
                    'melhor_tempo': round(min(tempos_validos), 2) if tempos_validos else 0,
                    'handicap_medio': round(sum(r.trio.handicap_total or 0 for r in resultados_cat) / len(resultados_cat), 1) if resultados_cat else 0,
                    'idade_media': round(sum(r.trio.idade_total or 0 for r in resultados_cat) / len(resultados_cat), 1) if resultados_cat else 0
                }

            return {
                'prova_id': prova_id,
                'total_categorias': len(comparacao),
                'comparacao_por_categoria': comparacao
            }
        except Exception as error:
            handle_error(error, self.comparar_performance_categorias)

    # ---------------------- Exportação e Importação ----------------------

    async def exportar_resultados_prova(self, prova_id: int, formato: str = 'json') -> Dict[str, Any]:
        """Exporta resultados de uma prova em formato estruturado"""
        try:
            resultados = await self.get_by_prova(prova_id)
            
            export_data = []
            for resultado in resultados:
                # Dados do trio
                integrantes = []
                for integrante in resultado.trio.integrantes:
                    comp = integrante.competidor
                    integrantes.append({
                        'competidor_id': comp.id,
                        'nome': comp.nome,
                        'handicap': comp.handicap,
                        'idade': comp.idade,
                        'cidade': comp.cidade,
                        'estado': comp.estado
                    })

                resultado_dict = {
                    'resultado_id': resultado.id,
                    'trio_id': resultado.trio_id,
                    'trio_numero': resultado.trio.numero_trio,
                    'categoria_nome': resultado.trio.categoria.nome,
                    'categoria_tipo': resultado.trio.categoria.tipo.value,
                    'integrantes': integrantes,
                    'handicap_total': resultado.trio.handicap_total,
                    'idade_total': resultado.trio.idade_total,
                    'passada1_tempo': resultado.passada1_tempo,
                    'passada2_tempo': resultado.passada2_tempo,
                    'media_tempo': resultado.media_tempo,
                    'colocacao': resultado.colocacao,
                    'premiacao_bruta': float(resultado.premiacao_valor or 0),
                    'premiacao_liquida': float(resultado.premiacao_liquida or 0),
                    'no_time': resultado.no_time,
                    'desclassificado': resultado.desclassificado,
                    'observacoes': resultado.observacoes
                }

                if formato == 'csv':
                    # Formato flat para CSV
                    resultado_flat = {}
                    resultado_flat.update({k: v for k, v in resultado_dict.items() if k != 'integrantes'})
                    
                    # Adicionar integrantes como colunas separadas
                    for i, integrante in enumerate(integrantes, 1):
                        for campo, valor in integrante.items():
                            resultado_flat[f'integrante_{i}_{campo}'] = valor
                    
                    export_data.append(resultado_flat)
                else:
                    export_data.append(resultado_dict)

            return {
                'prova_id': prova_id,
                'formato': formato,
                'total_resultados': len(export_data),
                'dados': export_data,
                'exportado_em': datetime.now().isoformat()
            }
        except Exception as error:
            handle_error(error, self.exportar_resultados_prova)

    async def importar_resultados_csv(self, prova_id: int, dados_csv: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Importa resultados de um arquivo CSV"""
        try:
            resultados_importados = 0
            erros = []

            for linha in dados_csv:
                try:
                    trio_numero = linha.get('trio_numero')
                    if not trio_numero:
                        erros.append("trio_numero é obrigatório")
                        continue

                    # Buscar trio pelo número
                    trio = self.db.execute(
                        select(schemas.Trios).where(
                            and_(
                                schemas.Trios.prova_id == prova_id,
                                schemas.Trios.numero_trio == trio_numero
                            )
                        )
                    ).scalars().first()

                    if not trio:
                        erros.append(f"Trio número {trio_numero} não encontrado")
                        continue

                    # Converter dados
                    resultado_data = models.ResultadoPOST(
                        trio_id=trio.id,
                        prova_id=prova_id,
                        passada1_tempo=float(linha['passada1_tempo']) if linha.get('passada1_tempo') else None,
                        passada2_tempo=float(linha['passada2_tempo']) if linha.get('passada2_tempo') else None,
                        colocacao=int(linha['colocacao']) if linha.get('colocacao') else None,
                        premiacao_valor=float(linha['premiacao_bruta']) if linha.get('premiacao_bruta') else None,
                        no_time=bool(linha.get('no_time', False)),
                        desclassificado=bool(linha.get('desclassificado', False)),
                        observacoes=linha.get('observacoes')
                    )

                    # Verificar se já existe
                    resultado_existente = await self.get_by_trio(trio.id)
                    
                    if resultado_existente:
                        # Atualizar
                        resultado_put = models.ResultadoPUT(**resultado_data.model_dump())
                        await self.put(resultado_existente.id, resultado_put)
                    else:
                        # Criar novo
                        await self.post(resultado_data)

                    resultados_importados += 1

                except Exception as e:
                    erros.append(f"Erro na linha {trio_numero}: {str(e)}")

            return {
                'resultados_importados': resultados_importados,
                'erros': erros,
                'sucesso': len(erros) == 0
            }
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.importar_resultados_csv)

    # ---------------------- Utilitários ----------------------

    async def recalcular_todos_os_campos(self, prova_id: int) -> bool:
        """Recalcula todos os campos derivados dos resultados de uma prova"""
        try:
            resultados = await self.get_by_prova(prova_id)
            
            for resultado in resultados:
                # Recalcular média e premiação líquida
                resultado.calcular_media()
                resultado.calcular_premiacao_liquida()
                
                # Atualizar no banco
                stmt = update(schemas.Resultados).where(
                    schemas.Resultados.id == resultado.id
                ).values(
                    media_tempo=resultado.media_tempo,
                    premiacao_liquida=resultado.premiacao_liquida
                )
                
                self.db.execute(stmt)

            self.db.commit()
            return True
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.recalcular_todos_os_campos)

    async def validar_consistencia_resultados(self, prova_id: int) -> Dict[str, Any]:
        """Valida consistência dos dados de resultados"""
        try:
            resultados = await self.get_by_prova(prova_id)
            
            inconsistencias = []
            
            for resultado in resultados:
                # Verificar colocação duplicada
                colocacao_duplicada = self.db.execute(
                    select(func.count(schemas.Resultados.id)).where(
                        and_(
                            schemas.Resultados.prova_id == prova_id,
                            schemas.Resultados.colocacao == resultado.colocacao,
                            schemas.Resultados.id != resultado.id
                        )
                    )
                ).scalar()

                if colocacao_duplicada > 0:
                    inconsistencias.append(f"Colocação {resultado.colocacao} duplicada (Trio {resultado.trio.numero_trio})")

                # Verificar tempos inválidos
                if resultado.passada1_tempo and resultado.passada1_tempo <= 0:
                    inconsistencias.append(f"Tempo passada 1 inválido no trio {resultado.trio.numero_trio}")

                if resultado.passada2_tempo and resultado.passada2_tempo <= 0:
                    inconsistencias.append(f"Tempo passada 2 inválido no trio {resultado.trio.numero_trio}")

                # Verificar média calculada
                if resultado.passada1_tempo and resultado.passada2_tempo:
                    media_esperada = (resultado.passada1_tempo + resultado.passada2_tempo) / 2
                    if abs((resultado.media_tempo or 0) - media_esperada) > 0.01:
                        inconsistencias.append(f"Média de tempo incorreta no trio {resultado.trio.numero_trio}")

                # Verificar no_time vs tempos
                if resultado.no_time and resultado.media_tempo:
                    inconsistencias.append(f"Trio {resultado.trio.numero_trio} marcado como no_time mas tem tempo médio")

                # Verificar premiação líquida
                if resultado.premiacao_valor and resultado.trio.prova:
                    desconto = resultado.trio.prova.percentual_desconto or 0
                    premiacao_esperada = float(resultado.premiacao_valor) * (1 - desconto / 100)
                    if abs((float(resultado.premiacao_liquida or 0) - premiacao_esperada)) > 0.01:
                        inconsistencias.append(f"Premiação líquida incorreta no trio {resultado.trio.numero_trio}")

            return {
                'prova_id': prova_id,
                'total_resultados': len(resultados),
                'total_inconsistencias': len(inconsistencias),
                'inconsistencias': inconsistencias,
                'valido': len(inconsistencias) == 0
            }
        except Exception as error:
            handle_error(error, self.validar_consistencia_resultados)