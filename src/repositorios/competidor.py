# repositorio_competidor.py
from sqlalchemy import select, delete, update, func, desc, asc
from sqlalchemy.orm import Session, joinedload, aliased
from src.database import models_lctp, schemas_lctp
from src.utils.error_handler import handle_error
from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any
import pytz

AMSP = pytz.timezone('America/Sao_Paulo')

class RepositorioCompetidor:
    
    def __init__(self, db: Session):
        self.db = db

    # ---------------------- Operações Básicas ----------------------

    async def get_by_id(self, competidor_id: int):
        """Recupera um competidor pelo ID"""
        try:
            stmt = select(schemas_lctp.Competidores).where(
                schemas_lctp.Competidores.id == competidor_id,
                schemas_lctp.Competidores.ativo == True
            )
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self.get_by_id)

    async def get_all(self, 
                      nome: Optional[str] = None,
                      handicap: Optional[int] = None,
                      cidade: Optional[str] = None,
                      estado: Optional[str] = None,
                      sexo: Optional[str] = None,
                      idade_min: Optional[int] = None,
                      idade_max: Optional[int] = None,
                      ativo: Optional[bool] = True,
                      pagina: Optional[int] = 0,
                      tamanho_pagina: Optional[int] = 0):
        """Recupera competidores com filtros"""
        try:
            c = aliased(schemas_lctp.Competidores)
            query = self.db.query(c)

            # Filtros
            if nome:
                query = query.filter(c.nome.ilike(f"%{nome}%"))
            if handicap is not None:
                query = query.filter(c.handicap == handicap)
            if cidade:
                query = query.filter(c.cidade.ilike(f"%{cidade}%"))
            if estado:
                query = query.filter(c.estado == estado)
            if sexo:
                query = query.filter(c.sexo == sexo)
            if ativo is not None:
                query = query.filter(c.ativo == ativo)
            
            # Filtro por idade (calculada)
            if idade_min or idade_max:
                hoje = date.today()
                if idade_min:
                    data_max = date(hoje.year - idade_min, hoje.month, hoje.day)
                    query = query.filter(c.data_nascimento <= data_max)
                if idade_max:
                    data_min = date(hoje.year - idade_max, hoje.month, hoje.day)
                    query = query.filter(c.data_nascimento >= data_min)

            # Ordenação
            query = query.order_by(c.nome)
            
            # Paginação
            if pagina > 0 and tamanho_pagina > 0:
                query = query.limit(tamanho_pagina).offset((pagina - 1) * tamanho_pagina)

            return query.all()
        except Exception as error:
            handle_error(error, self.get_all)

    async def post(self, orm: models_lctp.CompetidorPOST):
        """Cria um novo competidor"""
        try:
            db_orm = schemas_lctp.Competidores(
                nome=orm.nome,
                data_nascimento=orm.data_nascimento,
                handicap=orm.handicap,
                cidade=orm.cidade,
                estado=orm.estado,
                sexo=orm.sexo,
                ativo=orm.ativo
            )
            self.db.add(db_orm)
            self.db.commit()
            self.db.refresh(db_orm)
            return db_orm
        except Exception as error:
            handle_error(error, self.post)

    async def put(self, competidor_id: int, orm: models_lctp.CompetidorPUT):
        """Atualiza um competidor"""
        try:
            # Criar dicionário apenas com campos não None
            update_data = {k: v for k, v in orm.dict().items() if v is not None}
            update_data['updated_at'] = datetime.now(timezone.utc).astimezone(AMSP)
            
            stmt = update(schemas_lctp.Competidores).where(
                schemas_lctp.Competidores.id == competidor_id
            ).values(**update_data)
            
            self.db.execute(stmt)
            self.db.commit()
            
            return await self.get_by_id(competidor_id)
        except Exception as error:
            handle_error(error, self.put)

    async def delete(self, competidor_id: int):
        """Realiza exclusão lógica do competidor"""
        try:
            stmt = update(schemas_lctp.Competidores).where(
                schemas_lctp.Competidores.id == competidor_id
            ).values(
                ativo=False,
                deleted_at=datetime.now(timezone.utc).astimezone(AMSP)
            )
            self.db.execute(stmt)
            self.db.commit()
            return True
        except Exception as error:
            handle_error(error, self.delete)

    # ---------------------- Consultas Específicas ----------------------

    async def get_by_handicap(self, handicap: int):
        """Recupera competidores por handicap"""
        try:
            stmt = select(schemas_lctp.Competidores).where(
                schemas_lctp.Competidores.handicap == handicap,
                schemas_lctp.Competidores.ativo == True
            ).order_by(schemas_lctp.Competidores.nome)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_by_handicap)

    async def get_by_categoria_idade(self, idade_min: int, idade_max: int):
        """Recupera competidores por faixa etária"""
        try:
            hoje = date.today()
            data_max = date(hoje.year - idade_min, hoje.month, hoje.day)
            data_min = date(hoje.year - idade_max, hoje.month, hoje.day)
            
            stmt = select(schemas_lctp.Competidores).where(
                schemas_lctp.Competidores.data_nascimento.between(data_min, data_max),
                schemas_lctp.Competidores.ativo == True
            ).order_by(schemas_lctp.Competidores.nome)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_by_categoria_idade)

    async def get_femininos(self):
        """Recupera competidores do sexo feminino"""
        try:
            stmt = select(schemas_lctp.Competidores).where(
                schemas_lctp.Competidores.sexo == 'F',
                schemas_lctp.Competidores.ativo == True
            ).order_by(schemas_lctp.Competidores.nome)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_femininos)

    async def buscar_para_trio(self, categoria_id: int, excluir_ids: List[int] = None):
        """Busca competidores elegíveis para formar trio em uma categoria"""
        try:
            # Buscar regras da categoria
            categoria = await self.db.execute(
                select(schemas_lctp.Categorias).where(schemas_lctp.Categorias.id == categoria_id)
            ).scalars().first()
            
            if not categoria:
                return []

            query = self.db.query(schemas_lctp.Competidores).filter(
                schemas_lctp.Competidores.ativo == True
            )

            # Excluir IDs específicos (competidores já selecionados)
            if excluir_ids:
                query = query.filter(~schemas_lctp.Competidores.id.in_(excluir_ids))

            # Aplicar filtros baseados no tipo de categoria
            if categoria.tipo.value == 'feminina':
                query = query.filter(schemas_lctp.Competidores.sexo == 'F')
            
            # Filtros por idade individual
            if categoria.idade_min_individual or categoria.idade_max_individual:
                hoje = date.today()
                if categoria.idade_min_individual:
                    data_max = date(hoje.year - categoria.idade_min_individual, hoje.month, hoje.day)
                    query = query.filter(schemas_lctp.Competidores.data_nascimento <= data_max)
                if categoria.idade_max_individual:
                    data_min = date(hoje.year - categoria.idade_max_individual, hoje.month, hoje.day)
                    query = query.filter(schemas_lctp.Competidores.data_nascimento >= data_min)

            return query.order_by(schemas_lctp.Competidores.nome).all()
        except Exception as error:
            handle_error(error, self.buscar_para_trio)

    # ---------------------- Ranking e Estatísticas ----------------------

    async def get_ranking_por_categoria(self, categoria_id: int, ano: Optional[int] = None):
        """Gera ranking de competidores por categoria"""
        try:
            # Base query joining pontuacao
            query = self.db.query(
                schemas_lctp.Competidores,
                func.sum(schemas_lctp.Pontuacao.pontos_total).label('total_pontos'),
                func.count(schemas_lctp.Pontuacao.id).label('total_provas'),
                func.min(schemas_lctp.Pontuacao.colocacao).label('melhor_colocacao'),
                func.sum(schemas_lctp.Pontuacao.premiacao_valor).label('premiacao_total')
            ).join(
                schemas_lctp.Pontuacao, 
                schemas_lctp.Competidores.id == schemas_lctp.Pontuacao.competidor_id
            ).filter(
                schemas_lctp.Pontuacao.categoria_id == categoria_id,
                schemas_lctp.Competidores.ativo == True
            )

            # Filtro por ano se especificado
            if ano:
                query = query.join(schemas_lctp.Provas).filter(
                    func.extract('year', schemas_lctp.Provas.data) == ano
                )

            # Agrupar e ordenar
            query = query.group_by(schemas_lctp.Competidores.id).order_by(
                desc('total_pontos'), asc('melhor_colocacao')
            )

            return query.all()
        except Exception as error:
            handle_error(error, self.get_ranking_por_categoria)

    async def get_estatisticas_competidor(self, competidor_id: int):
        """Recupera estatísticas completas de um competidor"""
        try:
            # Estatísticas gerais
            stats = self.db.query(
                func.sum(schemas_lctp.Pontuacao.pontos_total).label('total_pontos'),
                func.count(schemas_lctp.Pontuacao.id).label('total_provas'),
                func.min(schemas_lctp.Pontuacao.colocacao).label('melhor_colocacao'),
                func.avg(schemas_lctp.Pontuacao.colocacao).label('colocacao_media'),
                func.sum(schemas_lctp.Pontuacao.premiacao_valor).label('premiacao_total')
            ).filter(
                schemas_lctp.Pontuacao.competidor_id == competidor_id
            ).first()

            # Estatísticas por categoria
            stats_categoria = self.db.query(
                schemas_lctp.Categorias.nome,
                func.sum(schemas_lctp.Pontuacao.pontos_total).label('pontos'),
                func.count(schemas_lctp.Pontuacao.id).label('provas'),
                func.min(schemas_lctp.Pontuacao.colocacao).label('melhor_colocacao')
            ).join(
                schemas_lctp.Pontuacao, 
                schemas_lctp.Categorias.id == schemas_lctp.Pontuacao.categoria_id
            ).filter(
                schemas_lctp.Pontuacao.competidor_id == competidor_id
            ).group_by(
                schemas_lctp.Categorias.id, schemas_lctp.Categorias.nome
            ).order_by(desc('pontos')).all()

            # Últimas participações
            ultimas_participacoes = self.db.query(
                schemas_lctp.Provas.nome,
                schemas_lctp.Provas.data,
                schemas_lctp.Categorias.nome.label('categoria'),
                schemas_lctp.Pontuacao.colocacao,
                schemas_lctp.Pontuacao.pontos_total,
                schemas_lctp.Pontuacao.premiacao_valor
            ).join(
                schemas_lctp.Pontuacao, 
                schemas_lctp.Provas.id == schemas_lctp.Pontuacao.prova_id
            ).join(
                schemas_lctp.Categorias,
                schemas_lctp.Categorias.id == schemas_lctp.Pontuacao.categoria_id
            ).filter(
                schemas_lctp.Pontuacao.competidor_id == competidor_id
            ).order_by(
                desc(schemas_lctp.Provas.data)
            ).limit(10).all()

            return {
                'estatisticas_gerais': stats,
                'estatisticas_por_categoria': stats_categoria,
                'ultimas_participacoes': ultimas_participacoes
            }
        except Exception as error:
            handle_error(error, self.get_estatisticas_competidor)

    async def get_campeoes_por_handicap(self, ano: Optional[int] = None):
        """Identifica campeões por handicap para Copa dos Campeões"""
        try:
            # Query base para ranking por handicap
            query = self.db.query(
                schemas_lctp.Competidores.handicap,
                schemas_lctp.Competidores.id,
                schemas_lctp.Competidores.nome,
                func.sum(schemas_lctp.Pontuacao.pontos_total).label('total_pontos'),
                func.row_number().over(
                    partition_by=schemas_lctp.Competidores.handicap,
                    order_by=desc(func.sum(schemas_lctp.Pontuacao.pontos_total))
                ).label('ranking')
            ).join(
                schemas_lctp.Pontuacao,
                schemas_lctp.Competidores.id == schemas_lctp.Pontuacao.competidor_id
            ).join(
                schemas_lctp.Provas,
                schemas_lctp.Provas.id == schemas_lctp.Pontuacao.prova_id
            ).filter(
                schemas_lctp.Competidores.ativo == True
            )

            # Filtro por ano
            if ano:
                query = query.filter(
                    func.extract('year', schemas_lctp.Provas.data) == ano
                )

            # Agrupar por competidor
            query = query.group_by(
                schemas_lctp.Competidores.id,
                schemas_lctp.Competidores.handicap,
                schemas_lctp.Competidores.nome
            )

            # Executar como subquery e filtrar apenas os primeiros colocados
            subquery = query.subquery()
            
            final_query = self.db.query(subquery).filter(
                subquery.c.ranking == 1
            ).order_by(subquery.c.handicap)

            return final_query.all()
        except Exception as error:
            handle_error(error, self.get_campeoes_por_handicap)

    # ---------------------- Validações e Regras de Negócio ----------------------

    async def validar_trio_handicap(self, competidores_ids: List[int], categoria_id: int):
        """Valida se o trio atende às regras de handicap da categoria"""
        try:
            # Buscar categoria
            categoria = await self.db.execute(
                select(schemas_lctp.Categorias).where(schemas_lctp.Categorias.id == categoria_id)
            ).scalars().first()

            if not categoria:
                return False, "Categoria não encontrada"

            # Buscar competidores
            competidores = await self.db.execute(
                select(schemas_lctp.Competidores).where(
                    schemas_lctp.Competidores.id.in_(competidores_ids)
                )
            ).scalars().all()

            if len(competidores) != 3:
                return False, "Trio deve ter exatamente 3 competidores"

            # Calcular totais
            handicap_total = sum(c.handicap for c in competidores)
            
            # Calcular idades
            hoje = date.today()
            idades = []
            for c in competidores:
                idade = hoje.year - c.data_nascimento.year
                if (hoje.month, hoje.day) < (c.data_nascimento.month, c.data_nascimento.day):
                    idade -= 1
                idades.append(idade)
            
            idade_total = sum(idades)

            # Validar handicap máximo
            if categoria.handicap_max_trio and handicap_total > categoria.handicap_max_trio:
                return False, f"Handicap total ({handicap_total}) excede o máximo permitido ({categoria.handicap_max_trio})"

            # Validar idade máxima
            if categoria.idade_max_trio and idade_total > categoria.idade_max_trio:
                return False, f"Idade total ({idade_total}) excede o máximo permitido ({categoria.idade_max_trio})"

            # Validar categoria feminina
            if categoria.tipo.value == 'feminina':
                competidores_femininos = [c for c in competidores if c.sexo == 'F']
                if len(competidores_femininos) != 3:
                    return False, "Categoria feminina deve ter apenas competidoras do sexo feminino"

            return True, "Trio válido"
        except Exception as error:
            handle_error(error, self.validar_trio_handicap)

    async def buscar_disponiveis_para_prova(self, prova_id: int, categoria_id: int):
        """Busca competidores disponíveis para uma prova (não inscritos ainda)"""
        try:
            # Subquery para competidores já inscritos na prova/categoria
            inscritos_subquery = self.db.query(
                schemas_lctp.IntegrantesTrios.competidor_id
            ).join(
                schemas_lctp.Trios,
                schemas_lctp.Trios.id == schemas_lctp.IntegrantesTrios.trio_id
            ).filter(
                schemas_lctp.Trios.prova_id == prova_id,
                schemas_lctp.Trios.categoria_id == categoria_id
            ).subquery()

            # Query principal excluindo já inscritos
            competidores_disponiveis = await self.buscar_para_trio(categoria_id)
            
            # Filtrar os já inscritos
            ids_inscritos = [row.competidor_id for row in inscritos_subquery]
            competidores_filtrados = [
                c for c in competidores_disponiveis 
                if c.id not in ids_inscritos
            ]

            return competidores_filtrados
        except Exception as error:
            handle_error(error, self.buscar_disponiveis_para_prova)

    # ---------------------- Relatórios e Exportação ----------------------

    async def relatorio_participacao_por_periodo(self, data_inicio: date, data_fim: date):
        """Gera relatório de participação por período"""
        try:
            relatorio = self.db.query(
                schemas_lctp.Competidores.id,
                schemas_lctp.Competidores.nome,
                schemas_lctp.Competidores.handicap,
                func.count(schemas_lctp.Pontuacao.id).label('total_participacoes'),
                func.sum(schemas_lctp.Pontuacao.pontos_total).label('total_pontos'),
                func.avg(schemas_lctp.Pontuacao.colocacao).label('colocacao_media'),
                func.sum(schemas_lctp.Pontuacao.premiacao_valor).label('premiacao_total')
            ).join(
                schemas_lctp.Pontuacao,
                schemas_lctp.Competidores.id == schemas_lctp.Pontuacao.competidor_id
            ).join(
                schemas_lctp.Provas,
                schemas_lctp.Provas.id == schemas_lctp.Pontuacao.prova_id
            ).filter(
                schemas_lctp.Provas.data.between(data_inicio, data_fim),
                schemas_lctp.Competidores.ativo == True
            ).group_by(
                schemas_lctp.Competidores.id,
                schemas_lctp.Competidores.nome,
                schemas_lctp.Competidores.handicap
            ).order_by(
                desc('total_pontos')
            ).all()

            return relatorio
        except Exception as error:
            handle_error(error, self.relatorio_participacao_por_periodo)

    async def get_historico_handicap(self, competidor_id: int):
        """Recupera histórico de mudanças de handicap (se implementado)"""
        try:
            # Por enquanto retorna o handicap atual
            # Futuramente pode ser implementada uma tabela de histórico
            competidor = await self.get_by_id(competidor_id)
            if competidor:
                return [{
                    'data': competidor.created_at or datetime.now(),
                    'handicap': competidor.handicap,
                    'motivo': 'Registro inicial'
                }]
            return []
        except Exception as error:
            handle_error(error, self.get_historico_handicap)

    # ---------------------- Operações em Lote ----------------------

    async def criar_multiplos(self, competidores: List[models_lctp.CompetidorPOST]):
        """Cria múltiplos competidores em uma transação"""
        try:
            competidores_criados = []
            for comp_data in competidores:
                db_orm = schemas_lctp.Competidores(
                    nome=comp_data.nome,
                    data_nascimento=comp_data.data_nascimento,
                    handicap=comp_data.handicap,
                    cidade=comp_data.cidade,
                    estado=comp_data.estado,
                    sexo=comp_data.sexo,
                    ativo=comp_data.ativo
                )
                self.db.add(db_orm)
                competidores_criados.append(db_orm)
            
            self.db.commit()
            
            # Refresh todos os objetos
            for comp in competidores_criados:
                self.db.refresh(comp)
            
            return competidores_criados
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.criar_multiplos)

    async def atualizar_handicaps_em_lote(self, updates: List[Dict[str, Any]]):
        """Atualiza handicaps de múltiplos competidores"""
        try:
            # updates = [{'id': 1, 'handicap': 3}, {'id': 2, 'handicap': 4}]
            for update in updates:
                stmt = update(schemas_lctp.Competidores).where(
                    schemas_lctp.Competidores.id == update['id']
                ).values(
                    handicap=update['handicap'],
                    updated_at=datetime.now(timezone.utc).astimezone(AMSP)
                )
                self.db.execute(stmt)
            
            self.db.commit()
            return True
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.atualizar_handicaps_em_lote)

    # ---------------------- Estatísticas Avançadas ----------------------

    async def get_performance_trends(self, competidor_id: int, limite_provas: int = 10):
        """Analisa tendências de performance do competidor"""
        try:
            # Últimas participações ordenadas por data
            participacoes = self.db.query(
                schemas_lctp.Provas.data,
                schemas_lctp.Pontuacao.colocacao,
                schemas_lctp.Pontuacao.pontos_total,
                schemas_lctp.Categorias.nome.label('categoria')
            ).join(
                schemas_lctp.Pontuacao,
                schemas_lctp.Provas.id == schemas_lctp.Pontuacao.prova_id
            ).join(
                schemas_lctp.Categorias,
                schemas_lctp.Categorias.id == schemas_lctp.Pontuacao.categoria_id
            ).filter(
                schemas_lctp.Pontuacao.competidor_id == competidor_id
            ).order_by(
                desc(schemas_lctp.Provas.data)
            ).limit(limite_provas).all()

            if not participacoes:
                return None

            # Calcular tendências
            colocacoes = [p.colocacao for p in participacoes if p.colocacao]
            pontos = [p.pontos_total for p in participacoes]
            
            analise = {
                'total_participacoes': len(participacoes),
                'colocacao_media': sum(colocacoes) / len(colocacoes) if colocacoes else None,
                'pontos_medio': sum(pontos) / len(pontos) if pontos else 0,
                'melhor_colocacao': min(colocacoes) if colocacoes else None,
                'pior_colocacao': max(colocacoes) if colocacoes else None,
                'tendencia_colocacao': 'melhorando' if len(colocacoes) >= 3 and 
                                     colocacoes[0] < colocacoes[-1] else 'estável',
                'participacoes_detalhadas': participacoes
            }

            return analise
        except Exception as error:
            handle_error(error, self.get_performance_trends)

    async def get_compatibilidade_trio(self, competidor_id: int, categoria_id: int):
        """Sugere competidores compatíveis para formar trio"""
        try:
            competidor = await self.get_by_id(competidor_id)
            if not competidor:
                return []

            categoria = await self.db.execute(
                select(schemas_lctp.Categorias).where(schemas_lctp.Categorias.id == categoria_id)
            ).scalars().first()

            if not categoria:
                return []

            # Buscar competidores elegíveis
            compativeis = await self.buscar_para_trio(categoria_id, [competidor_id])
            
            # Filtrar baseado nas regras da categoria
            sugestoes = []
            for comp1 in compativeis:
                for comp2 in compativeis:
                    if comp1.id >= comp2.id:  # Evitar duplicatas
                        continue
                    
                    # Validar se o trio seria válido
                    valido, _ = await self.validar_trio_handicap(
                        [competidor_id, comp1.id, comp2.id], 
                        categoria_id
                    )
                    
                    if valido:
                        handicap_total = competidor.handicap + comp1.handicap + comp2.handicap
                        
                        # Calcular idades
                        hoje = date.today()
                        idade_comp = hoje.year - competidor.data_nascimento.year
                        idade_comp1 = hoje.year - comp1.data_nascimento.year
                        idade_comp2 = hoje.year - comp2.data_nascimento.year
                        idade_total = idade_comp + idade_comp1 + idade_comp2
                        
                        sugestoes.append({
                            'competidor1': comp1,
                            'competidor2': comp2,
                            'handicap_total': handicap_total,
                            'idade_total': idade_total,
                            'score_compatibilidade': self._calcular_score_compatibilidade(
                                competidor, comp1, comp2, categoria
                            )
                        })
            
            # Ordenar por score de compatibilidade
            sugestoes.sort(key=lambda x: x['score_compatibilidade'], reverse=True)
            return sugestoes[:10]  # Top 10 sugestões
            
        except Exception as error:
            handle_error(error, self.get_compatibilidade_trio)

    def _calcular_score_compatibilidade(self, comp_base, comp1, comp2, categoria):
        """Calcula score de compatibilidade para formação de trio"""
        score = 100
        
        # Penalizar se muito próximo dos limites
        handicap_total = comp_base.handicap + comp1.handicap + comp2.handicap
        if categoria.handicap_max_trio:
            if handicap_total > categoria.handicap_max_trio * 0.9:
                score -= 20
        
        # Bonificar equilíbrio de handicaps
        handicaps = [comp_base.handicap, comp1.handicap, comp2.handicap]
        if max(handicaps) - min(handicaps) <= 2:
            score += 10
        
        # Bonificar mesma região
        if comp_base.estado and comp1.estado == comp_base.estado:
            score += 5
        if comp_base.estado and comp2.estado == comp_base.estado:
            score += 5
            
        return score