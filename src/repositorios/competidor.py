# repositorio_competidor.py
from sqlalchemy import select, delete, update, func, desc, asc, and_, or_
from sqlalchemy.orm import Session, joinedload, aliased
from src.database import models, schemas
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
        """Recupera um competidor pelo ID com categoria"""
        try:
            stmt = select(schemas.Competidores).options(
                joinedload(schemas.Competidores.categoria)
            ).where(
                schemas.Competidores.id == competidor_id,
                schemas.Competidores.ativo == True
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
                  categoria_id: Optional[int] = None,
                  categoria_tipo: Optional[str] = None,
                  apenas_com_categoria: Optional[bool] = None,
                  pagina: Optional[int] = 0,
                  tamanho_pagina: Optional[int] = 0):
        """Recupera competidores com filtros incluindo categoria"""
        try:
            c = aliased(schemas.Competidores)
            cat = aliased(schemas.Categorias)
            
            # Query com SELECT explícito para incluir categoria_nome
            query = self.db.query(
                c.id,
                c.nome,
                c.data_nascimento,
                c.handicap,
                c.categoria_id,
                c.cidade,
                c.estado,
                c.sexo,
                c.ativo,
                c.created_at,
                c.updated_at,
                cat.nome.label('categoria_nome')
            ).outerjoin(cat, c.categoria_id == cat.id)

            # Filtros básicos
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
            
            # Filtros por categoria
            if categoria_id:
                query = query.filter(c.categoria_id == categoria_id)
            if categoria_tipo:
                query = query.filter(cat.tipo == categoria_tipo)
            if apenas_com_categoria is not None:
                if apenas_com_categoria:
                    query = query.filter(c.categoria_id.isnot(None))
                else:
                    query = query.filter(c.categoria_id.is_(None))
            
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

    async def post(self, orm: models.CompetidorPOST):
        """Cria um novo competidor com categoria sugerida"""
        try:
            # Determinar categoria sugerida se não informada
            categoria_id = orm.categoria_id
            if not categoria_id:
                categoria_id = await self._sugerir_categoria_automatica(orm)

            db_orm = schemas.Competidores(
                nome=orm.nome,
                data_nascimento=orm.data_nascimento,
                handicap=orm.handicap,
                categoria_id=categoria_id,
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

    async def put(self, competidor_id: int, orm: models.CompetidorPUT):
        """Atualiza um competidor"""
        try:
            # Criar dicionário apenas com campos não None
            update_data = {k: v for k, v in orm.dict().items() if v is not None}
            update_data['updated_at'] = datetime.now(timezone.utc).astimezone(AMSP)
            
            stmt = update(schemas.Competidores).where(
                schemas.Competidores.id == competidor_id
            ).values(**update_data)
            
            self.db.execute(stmt)
            self.db.commit()
            
            return await self.get_by_id(competidor_id)
        except Exception as error:
            handle_error(error, self.put)

    async def delete(self, competidor_id: int):
        """Realiza exclusão lógica do competidor"""
        try:
            stmt = update(schemas.Competidores).where(
                schemas.Competidores.id == competidor_id
            ).values(
                ativo=False,
                deleted_at=datetime.now(timezone.utc).astimezone(AMSP)
            )
            self.db.execute(stmt)
            self.db.commit()
            return True
        except Exception as error:
            handle_error(error, self.delete)

    # ---------------------- Consultas por Categoria ----------------------

    async def get_by_categoria(self, categoria_id: int):
        """Recupera competidores de uma categoria específica"""
        try:
            stmt = select(schemas.Competidores).where(
                schemas.Competidores.categoria_id == categoria_id,
                schemas.Competidores.ativo == True
            ).order_by(schemas.Competidores.nome)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_by_categoria)

    async def get_sem_categoria(self):
        """Recupera competidores sem categoria definida"""
        try:
            stmt = select(schemas.Competidores).where(
                schemas.Competidores.categoria_id.is_(None),
                schemas.Competidores.ativo == True
            ).order_by(schemas.Competidores.nome)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_sem_categoria)

    async def atualizar_categoria(self, competidor_id: int, categoria_id: Optional[int]):
        """Atualiza apenas a categoria do competidor"""
        try:
            stmt = update(schemas.Competidores).where(
                schemas.Competidores.id == competidor_id
            ).values(
                categoria_id=categoria_id,
                updated_at=datetime.now(timezone.utc).astimezone(AMSP)
            )
            
            self.db.execute(stmt)
            self.db.commit()
            
            return await self.get_by_id(competidor_id)
        except Exception as error:
            handle_error(error, self.atualizar_categoria)

    async def sugerir_categoria(self, competidor_id: int):
        """Sugere categoria baseada nas regras"""
        try:
            competidor = await self.get_by_id(competidor_id)
            if not competidor:
                return None

            # Calcular idade
            hoje = date.today()
            idade = hoje.year - competidor.data_nascimento.year
            if (hoje.month, hoje.day) < (competidor.data_nascimento.month, competidor.data_nascimento.day):
                idade -= 1

            sugestoes = []

            # Baby (até 12 anos)
            if idade <= 12:
                categoria_baby = await self._buscar_categoria_por_tipo('baby')
                if categoria_baby:
                    sugestoes.append({
                        'categoria': categoria_baby,
                        'motivo': f'Idade {idade} anos - elegível para categoria Baby',
                        'prioridade': 1
                    })

            # Kids (13-17 anos)
            elif 13 <= idade <= 17:
                categoria_kids = await self._buscar_categoria_por_tipo('kids')
                if categoria_kids:
                    sugestoes.append({
                        'categoria': categoria_kids,
                        'motivo': f'Idade {idade} anos - elegível para categoria Kids',
                        'prioridade': 1
                    })

            # Feminina (se for mulher)
            if competidor.sexo == 'F':
                categoria_feminina = await self._buscar_categoria_por_tipo('feminina')
                if categoria_feminina:
                    prioridade = 1 if idade >= 18 else 2
                    sugestoes.append({
                        'categoria': categoria_feminina,
                        'motivo': 'Competidora feminina - elegível para categoria Feminina',
                        'prioridade': prioridade
                    })

            # Mirim (idade permite formar trio ≤ 36 anos)
            if idade <= 36:
                categoria_mirim = await self._buscar_categoria_por_tipo('mirim')
                if categoria_mirim:
                    sugestoes.append({
                        'categoria': categoria_mirim,
                        'motivo': f'Idade {idade} anos - pode participar de trio Mirim',
                        'prioridade': 2
                    })

            # Handicap (baseado no handicap)
            categoria_handicap = await self._buscar_categoria_por_tipo('handicap')
            if categoria_handicap:
                sugestoes.append({
                    'categoria': categoria_handicap,
                    'motivo': f'Handicap {competidor.handicap} - elegível para categoria Handicap',
                    'prioridade': 3
                })

            # Aberta (sempre elegível)
            categoria_aberta = await self._buscar_categoria_por_tipo('aberta')
            if categoria_aberta:
                sugestoes.append({
                    'categoria': categoria_aberta,
                    'motivo': 'Sempre elegível para categoria Aberta',
                    'prioridade': 4
                })

            # Ordenar por prioridade
            sugestoes.sort(key=lambda x: x['prioridade'])
            
            return sugestoes

        except Exception as error:
            handle_error(error, self.sugerir_categoria)

    async def _sugerir_categoria_automatica(self, competidor_data: models.CompetidorPOST) -> Optional[int]:
        """Sugere categoria automaticamente baseada nos dados"""
        try:
            # Calcular idade
            hoje = date.today()
            idade = hoje.year - competidor_data.data_nascimento.year
            if (hoje.month, hoje.day) < (competidor_data.data_nascimento.month, competidor_data.data_nascimento.day):
                idade -= 1

            # Baby tem prioridade absoluta
            if idade <= 12:
                categoria = await self._buscar_categoria_por_tipo('baby')
                return categoria.id if categoria else None

            # Kids tem prioridade para 13-17 anos
            if 13 <= idade <= 17:
                categoria = await self._buscar_categoria_por_tipo('kids')
                return categoria.id if categoria else None

            # Para adultos, feminina tem prioridade se for mulher
            if competidor_data.sexo == 'F':
                categoria = await self._buscar_categoria_por_tipo('feminina')
                return categoria.id if categoria else None

            # Padrão: categoria aberta
            categoria = await self._buscar_categoria_por_tipo('aberta')
            return categoria.id if categoria else None

        except Exception as error:
            handle_error(error, self._sugerir_categoria_automatica)
            return None

    async def _buscar_categoria_por_tipo(self, tipo: str):
        """Busca categoria ativa por tipo"""
        try:
            stmt = select(schemas.Categorias).where(
                schemas.Categorias.tipo == tipo,
                schemas.Categorias.ativa == True
            )
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self._buscar_categoria_por_tipo)
            return None

    # ---------------------- Consultas Específicas ----------------------

    async def get_by_handicap(self, handicap: int):
        """Recupera competidores por handicap"""
        try:
            stmt = select(schemas.Competidores).where(
                schemas.Competidores.handicap == handicap,
                schemas.Competidores.ativo == True
            ).order_by(schemas.Competidores.nome)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_by_handicap)

    async def get_by_categoria_idade(self, idade_min: int, idade_max: int):
        """Recupera competidores por faixa etária"""
        try:
            hoje = date.today()
            data_max = date(hoje.year - idade_min, hoje.month, hoje.day)
            data_min = date(hoje.year - idade_max, hoje.month, hoje.day)
            
            stmt = select(schemas.Competidores).where(
                schemas.Competidores.data_nascimento.between(data_min, data_max),
                schemas.Competidores.ativo == True
            ).order_by(schemas.Competidores.nome)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_by_categoria_idade)

    async def get_femininos(self):
        """Recupera competidores do sexo feminino"""
        try:
            stmt = select(schemas.Competidores).where(
                schemas.Competidores.sexo == 'F',
                schemas.Competidores.ativo == True
            ).order_by(schemas.Competidores.nome)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_femininos)

    def buscar_para_trio(self, categoria_id: int, excluir_ids: List[int] = None):
        """Busca competidores elegíveis para formar trio em uma categoria"""
        try:
            # Buscar regras da categoria
            categoria = self.db.execute(
                select(schemas.Categorias).where(schemas.Categorias.id == categoria_id)
            ).scalars().first()
            
            if not categoria:
                return []

            query = self.db.query(schemas.Competidores).filter(
                schemas.Competidores.ativo == True,
                schemas.Competidores.categoria_id == categoria_id 
            )

            # Excluir IDs específicos (competidores já selecionados)
            if excluir_ids:
                query = query.filter(~schemas.Competidores.id.in_(excluir_ids))

            # Aplicar filtros baseados no tipo de categoria
            if categoria.tipo == 'feminina':
                query = query.filter(schemas.Competidores.sexo == 'F')
            
            # Filtros por idade individual
            if categoria.idade_min_individual or categoria.idade_max_individual:
                hoje = date.today()
                if categoria.idade_min_individual:
                    data_max = date(hoje.year - categoria.idade_min_individual, hoje.month, hoje.day)
                    query = query.filter(schemas.Competidores.data_nascimento <= data_max)
                if categoria.idade_max_individual:
                    data_min = date(hoje.year - categoria.idade_max_individual, hoje.month, hoje.day)
                    query = query.filter(schemas.Competidores.data_nascimento >= data_min)

            # Priorizar competidores da mesma categoria, mas permitir outros
            competidores = query.order_by(
                (schemas.Competidores.categoria_id == categoria_id).desc(),
                schemas.Competidores.nome
            ).all()

            return competidores
        except Exception as error:
            handle_error(error, self.buscar_para_trio)

    # ---------------------- Operações em Lote de Categoria ----------------------

    async def migrar_categorias(self, competidores_ids: List[int], categoria_destino_id: int):
        """Migra múltiplos competidores para uma categoria"""
        try:
            stmt = update(schemas.Competidores).where(
                schemas.Competidores.id.in_(competidores_ids)
            ).values(
                categoria_id=categoria_destino_id,
                updated_at=datetime.now(timezone.utc).astimezone(AMSP)
            )
            
            result = self.db.execute(stmt)
            self.db.commit()
            
            return result.rowcount
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.migrar_categorias)

    async def atualizar_categorias_automaticamente(self):
        """Atualiza categorias de todos os competidores baseado nas regras"""
        try:
            competidores_sem_categoria = await self.get_sem_categoria()
            atualizados = 0
            
            for competidor in competidores_sem_categoria:
                categoria_id = await self._sugerir_categoria_automatica_por_competidor(competidor)
                if categoria_id:
                    await self.atualizar_categoria(competidor.id, categoria_id)
                    atualizados += 1
            
            return atualizados
        except Exception as error:
            handle_error(error, self.atualizar_categorias_automaticamente)

    async def _sugerir_categoria_automatica_por_competidor(self, competidor) -> Optional[int]:
        """Sugere categoria para um competidor existente"""
        try:
            fake_post = models.CompetidorPOST(
                nome=competidor.nome,
                data_nascimento=competidor.data_nascimento,
                handicap=competidor.handicap,
                cidade=competidor.cidade,
                estado=competidor.estado,
                sexo=competidor.sexo,
                ativo=competidor.ativo
            )
            return await self._sugerir_categoria_automatica(fake_post)
        except Exception as error:
            handle_error(error, self._sugerir_categoria_automatica_por_competidor)
            return None

    # ---------------------- Estatísticas com Categoria ----------------------

    async def get_estatisticas_por_categoria(self):
        """Gera estatísticas de competidores por categoria"""
        try:
            stats = self.db.query(
                schemas.Categorias.id,
                schemas.Categorias.nome,
                schemas.Categorias.tipo,
                func.count(schemas.Competidores.id).label('total_competidores'),
                func.count(schemas.Competidores.id).filter(schemas.Competidores.ativo == True).label('competidores_ativos'),
                func.avg(schemas.Competidores.handicap).label('media_handicap'),
                func.count(schemas.Competidores.id).filter(schemas.Competidores.sexo == 'F').label('total_feminino'),
                func.count(schemas.Competidores.id).filter(schemas.Competidores.sexo == 'M').label('total_masculino')
            ).outerjoin(
                schemas.Competidores,
                schemas.Categorias.id == schemas.Competidores.categoria_id
            ).group_by(
                schemas.Categorias.id,
                schemas.Categorias.nome,
                schemas.Categorias.tipo
            ).order_by(schemas.Categorias.nome).all()

            # Adicionar competidores sem categoria
            sem_categoria = self.db.query(
                func.count(schemas.Competidores.id).label('total_sem_categoria'),
                func.count(schemas.Competidores.id).filter(schemas.Competidores.ativo == True).label('ativos_sem_categoria')
            ).filter(schemas.Competidores.categoria_id.is_(None)).first()

            return {
                'por_categoria': stats,
                'sem_categoria': sem_categoria
            }
        except Exception as error:
            handle_error(error, self.get_estatisticas_por_categoria)

    # ---------------------- Ranking e Estatísticas ----------------------

    async def get_ranking_por_categoria(self, categoria_id: int, ano: Optional[int] = None):
        """Gera ranking de competidores por categoria"""
        try:
            # Base query joining pontuacao
            query = self.db.query(
                schemas.Competidores,
                func.sum(schemas.Pontuacao.pontos_total).label('total_pontos'),
                func.count(schemas.Pontuacao.id).label('total_provas'),
                func.min(schemas.Pontuacao.colocacao).label('melhor_colocacao'),
                func.sum(schemas.Pontuacao.premiacao_valor).label('premiacao_total')
            ).join(
                schemas.Pontuacao, 
                schemas.Competidores.id == schemas.Pontuacao.competidor_id
            ).filter(
                schemas.Pontuacao.categoria_id == categoria_id,
                schemas.Competidores.ativo == True
            )

            # Filtro por ano se especificado
            if ano:
                query = query.join(schemas.Provas).filter(
                    func.extract('year', schemas.Provas.data) == ano
                )

            # Agrupar e ordenar
            query = query.group_by(schemas.Competidores.id).order_by(
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
                func.sum(schemas.Pontuacao.pontos_total).label('total_pontos'),
                func.count(schemas.Pontuacao.id).label('total_provas'),
                func.min(schemas.Pontuacao.colocacao).label('melhor_colocacao'),
                func.avg(schemas.Pontuacao.colocacao).label('colocacao_media'),
                func.sum(schemas.Pontuacao.premiacao_valor).label('premiacao_total')
            ).filter(
                schemas.Pontuacao.competidor_id == competidor_id
            ).first()

            # Estatísticas por categoria
            stats_categoria = self.db.query(
                schemas.Categorias.nome,
                func.sum(schemas.Pontuacao.pontos_total).label('pontos'),
                func.count(schemas.Pontuacao.id).label('provas'),
                func.min(schemas.Pontuacao.colocacao).label('melhor_colocacao')
            ).join(
                schemas.Pontuacao, 
                schemas.Categorias.id == schemas.Pontuacao.categoria_id
            ).filter(
                schemas.Pontuacao.competidor_id == competidor_id
            ).group_by(
                schemas.Categorias.id, schemas.Categorias.nome
            ).order_by(desc('pontos')).all()

            # Últimas participações
            ultimas_participacoes = self.db.query(
                schemas.Provas.nome,
                schemas.Provas.data,
                schemas.Categorias.nome.label('categoria'),
                schemas.Pontuacao.colocacao,
                schemas.Pontuacao.pontos_total,
                schemas.Pontuacao.premiacao_valor
            ).join(
                schemas.Pontuacao, 
                schemas.Provas.id == schemas.Pontuacao.prova_id
            ).join(
                schemas.Categorias,
                schemas.Categorias.id == schemas.Pontuacao.categoria_id
            ).filter(
                schemas.Pontuacao.competidor_id == competidor_id
            ).order_by(
                desc(schemas.Provas.data)
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
                schemas.Competidores.handicap,
                schemas.Competidores.id,
                schemas.Competidores.nome,
                func.sum(schemas.Pontuacao.pontos_total).label('total_pontos'),
                func.row_number().over(
                    partition_by=schemas.Competidores.handicap,
                    order_by=desc(func.sum(schemas.Pontuacao.pontos_total))
                ).label('ranking')
            ).join(
                schemas.Pontuacao,
                schemas.Competidores.id == schemas.Pontuacao.competidor_id
            ).join(
                schemas.Provas,
                schemas.Provas.id == schemas.Pontuacao.prova_id
            ).filter(
                schemas.Competidores.ativo == True
            )

            # Filtro por ano
            if ano:
                query = query.filter(
                    func.extract('year', schemas.Provas.data) == ano
                )

            # Agrupar por competidor
            query = query.group_by(
                schemas.Competidores.id,
                schemas.Competidores.handicap,
                schemas.Competidores.nome
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
            categoria =  self.db.execute(
                select(schemas.Categorias).where(schemas.Categorias.id == categoria_id)
            ).scalars().first()

            if not categoria:
                return False, "Categoria não encontrada"

            # Buscar competidores
            competidores = self.db.execute(
                select(schemas.Competidores).where(
                    schemas.Competidores.id.in_(competidores_ids)
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
                try:
                    idade = hoje.year - c.data_nascimento.year
                    if (hoje.month, hoje.day) < (c.data_nascimento.month, c.data_nascimento.day):
                        idade -= 1
                    idades.append(idade)
                except Exception as e:
                    return False, f"Erro ao calcular idade de {c.nome}: {e}"
            
            idade_total = sum(idades)

            # Validar handicap máximo
            if categoria.handicap_max_trio and handicap_total > categoria.handicap_max_trio:
                return False, f"Handicap total ({handicap_total}) excede o máximo permitido ({categoria.handicap_max_trio})"

            # Validar idade máxima
            if categoria.idade_max_trio and idade_total > categoria.idade_max_trio:
                return False, f"Idade total ({idade_total}) excede o máximo permitido ({categoria.idade_max_trio})"

            # Validar categoria feminina
            if categoria.tipo == 'feminina':
                competidores_femininos = [c for c in competidores if c.sexo == 'F']
                if len(competidores_femininos) != 3:
                    return False, "Categoria feminina deve ter apenas competidoras do sexo feminino"

            return True, "Trio válido"
        except Exception as error:
            handle_error(error, self.validar_trio_handicap)

    async def buscar_disponiveis_para_prova(self, prova_id: int, categoria_id: int, aplicar_filtros: bool = False):
        """Busca competidores disponíveis para uma prova verificando se podem competir"""
        try:
            if aplicar_filtros:
                # Usar buscar_para_trio com filtros (comportamento original)
                competidores_disponiveis = self.buscar_para_trio(categoria_id)
            else:
                # ✅ Buscar competidores da categoria específica que PODEM COMPETIR
                competidores_disponiveis = self.db.query(schemas.Competidores).join(
                    schemas.ControleParticipacao,
                    schemas.Competidores.id == schemas.ControleParticipacao.competidor_id
                ).filter(
                    schemas.Competidores.ativo == True,
                    schemas.Competidores.categoria_id == categoria_id,
                    schemas.ControleParticipacao.pode_competir == True  # ✅ VERIFICAR SE PODE COMPETIR
                ).order_by(schemas.Competidores.nome).all()

            # Buscar configuração da prova para obter max_corridas_por_pessoa
            config_prova = self.db.query(schemas.ConfiguracaoPassadasProva).filter(
                schemas.ConfiguracaoPassadasProva.prova_id == prova_id,
                schemas.ConfiguracaoPassadasProva.categoria_id == categoria_id
            ).first()
            
            max_corridas = config_prova.max_corridas_por_pessoa if config_prova else 5  # default 5

            # Contar quantas vezes cada competidor já está inscrito na prova/categoria
            ids_inscritos = self.db.query(
                schemas.IntegrantesTrios.competidor_id,
                func.count(schemas.IntegrantesTrios.competidor_id).label('total_inscricoes')
            ).join(
                schemas.Trios,
                schemas.Trios.id == schemas.IntegrantesTrios.trio_id
            ).filter(
                schemas.Trios.prova_id == prova_id,
                schemas.Trios.categoria_id == categoria_id
            ).group_by(schemas.IntegrantesTrios.competidor_id).all()

            ids_inscritos_list = [row.competidor_id for row in ids_inscritos if row.total_inscricoes >= max_corridas]

            # Filtrar apenas os não inscritos ou que não atingiram o limite
            competidores_filtrados = [
                c for c in competidores_disponiveis if c.id not in ids_inscritos_list
            ]

            return competidores_filtrados
            
        except Exception as error:
            handle_error(error, self.buscar_disponiveis_para_prova)
            return []

    async def verificar_controle_participacao(self, categoria_id: int):
        """Verifica status do controle de participação para uma categoria"""
        try:            
            # Contar competidores na categoria
            total_categoria = self.db.query(schemas.Competidores).filter(
                schemas.Competidores.categoria_id == categoria_id,
                schemas.Competidores.ativo == True
            ).count()
            
            
            # Verificar controle de participação
            query = self.db.query(
                schemas.Competidores.id,
                schemas.Competidores.nome,
                schemas.ControleParticipacao.pode_competir,
                schemas.ControleParticipacao.motivo_bloqueio
            ).outerjoin(
                schemas.ControleParticipacao,
                schemas.Competidores.id == schemas.ControleParticipacao.competidor_id
            ).filter(
                schemas.Competidores.categoria_id == categoria_id,
                schemas.Competidores.ativo == True
            ).all()
            
            pode_competir = 0
            nao_pode_competir = 0
            sem_controle = 0
            
            for comp_id, nome, pode_competir_flag, motivo in query:
                status = "✅ PODE" if pode_competir_flag is True else "❌ BLOQUEADO" if pode_competir_flag is False else "⚪ SEM CONTROLE"
                motivo_text = f" ({motivo})" if motivo else ""
                print(f"   {comp_id:3d} - {nome:30s} - {status}{motivo_text}")
                
                if pode_competir_flag is True:
                    pode_competir += 1
                elif pode_competir_flag is False:
                    nao_pode_competir += 1
                else:
                    sem_controle += 1
            
            return {
                'total_categoria': total_categoria,
                'pode_competir': pode_competir,
                'nao_pode_competir': nao_pode_competir,
                'sem_controle': sem_controle,
                'total_disponivel': pode_competir + sem_controle
            }
            
        except Exception as error:
            print(f"❌ Erro na verificação: {error}")
            return None

    # =================== MÉTODO PARA CRIAR CONTROLE DE PARTICIPAÇÃO ===================

    async def criar_controle_participacao_categoria(self, categoria_id: int, pode_competir: bool = True):
        """Cria controle de participação para todos os competidores de uma categoria"""
        try:
            
            # Buscar competidores sem controle
            competidores_sem_controle = self.db.query(schemas.Competidores).outerjoin(
                schemas.ControleParticipacao,
                schemas.Competidores.id == schemas.ControleParticipacao.competidor_id
            ).filter(
                schemas.Competidores.categoria_id == categoria_id,
                schemas.Competidores.ativo == True,
                schemas.ControleParticipacao.id.is_(None)  # Sem controle
            ).all()
                        
            criados = 0
            for competidor in competidores_sem_controle:
                controle = schemas.ControleParticipacao(
                    competidor_id=competidor.id,
                    pode_competir=pode_competir,
                    motivo_bloqueio=None if pode_competir else "Controle automático"
                )
                self.db.add(controle)
                criados += 1
            
            self.db.commit()
            
            return criados
            
        except Exception as error:
            print(f"❌ Erro ao criar controle: {error}")
            self.db.rollback()
            return 0

    # ---------------------- Relatórios e Exportação ----------------------

    async def relatorio_participacao_por_periodo(self, data_inicio: date, data_fim: date):
        """Gera relatório de participação por período"""
        try:
            relatorio = self.db.query(
                schemas.Competidores.id,
                schemas.Competidores.nome,
                schemas.Competidores.handicap,
                schemas.Categorias.nome.label('categoria_nome'),
                func.count(schemas.Pontuacao.id).label('total_participacoes'),
                func.sum(schemas.Pontuacao.pontos_total).label('total_pontos'),
                func.avg(schemas.Pontuacao.colocacao).label('colocacao_media'),
                func.sum(schemas.Pontuacao.premiacao_valor).label('premiacao_total')
            ).outerjoin(
                schemas.Categorias,
                schemas.Competidores.categoria_id == schemas.Categorias.id
            ).join(
                schemas.Pontuacao,
                schemas.Competidores.id == schemas.Pontuacao.competidor_id
            ).join(
                schemas.Provas,
                schemas.Provas.id == schemas.Pontuacao.prova_id
            ).filter(
                schemas.Provas.data.between(data_inicio, data_fim),
                schemas.Competidores.ativo == True
            ).group_by(
                schemas.Competidores.id,
                schemas.Competidores.nome,
                schemas.Competidores.handicap,
                schemas.Categorias.nome
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

    async def criar_multiplos(self, competidores: List[models.CompetidorPOST]):
        """Cria múltiplos competidores em uma transação"""
        try:
            competidores_criados = []
            for comp_data in competidores:
                # Determinar categoria sugerida se não informada
                categoria_id = comp_data.categoria_id
                if not categoria_id:
                    categoria_id = await self._sugerir_categoria_automatica(comp_data)

                db_orm = schemas.Competidores(
                    nome=comp_data.nome,
                    data_nascimento=comp_data.data_nascimento,
                    handicap=comp_data.handicap,
                    categoria_id=categoria_id,
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
                stmt = update(schemas.Competidores).where(
                    schemas.Competidores.id == update['id']
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
                schemas.Provas.data,
                schemas.Pontuacao.colocacao,
                schemas.Pontuacao.pontos_total,
                schemas.Categorias.nome.label('categoria')
            ).join(
                schemas.Pontuacao,
                schemas.Provas.id == schemas.Pontuacao.prova_id
            ).join(
                schemas.Categorias,
                schemas.Categorias.id == schemas.Pontuacao.categoria_id
            ).filter(
                schemas.Pontuacao.competidor_id == competidor_id
            ).order_by(
                desc(schemas.Provas.data)
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

            categoria = self.db.execute(
                select(schemas.Categorias).where(schemas.Categorias.id == categoria_id)
            ).scalars().first()

            if not categoria:
                return []

            # Buscar competidores elegíveis
            compativeis = self.buscar_para_trio(categoria_id, [competidor_id])
            
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

        # Bonificar mesma categoria
        if comp_base.categoria_id and comp1.categoria_id == comp_base.categoria_id:
            score += 10
        if comp_base.categoria_id and comp2.categoria_id == comp_base.categoria_id:
            score += 10
            
        return score

    async def get_competidor_com_categoria(self, competidor_id: int):
        """Recupera competidor com informações completas da categoria"""
        try:
            stmt = select(
                schemas.Competidores,
                schemas.Categorias.nome.label('categoria_nome'),
                schemas.Categorias.tipo.label('categoria_tipo'),
                schemas.Categorias.descricao.label('categoria_descricao')
            ).outerjoin(
                schemas.Categorias,
                schemas.Competidores.categoria_id == schemas.Categorias.id
            ).where(
                schemas.Competidores.id == competidor_id,
                schemas.Competidores.ativo == True
            )
            
            result = self.db.execute(stmt).first()
            return result
        except Exception as error:
            handle_error(error, self.get_competidor_com_categoria)

    async def validar_categoria_competidor(self, competidor_id: int, categoria_id: int):
        """Valida se um competidor pode ser associado a uma categoria"""
        try:
            competidor = await self.get_by_id(competidor_id)
            if not competidor:
                return False, "Competidor não encontrado"
            
            categoria = self.db.execute(
                select(schemas.Categorias).where(schemas.Categorias.id == categoria_id)
            ).scalars().first()
            
            if not categoria:
                return False, "Categoria não encontrada"
            
            # Calcular idade
            hoje = date.today()
            idade = hoje.year - competidor.data_nascimento.year
            if (hoje.month, hoje.day) < (competidor.data_nascimento.month, competidor.data_nascimento.day):
                idade -= 1
            
            # Validações por tipo de categoria
            if categoria.tipo == 'baby' and idade > 12:
                return False, f"Competidor com {idade} anos não pode participar da categoria Baby (máx 12 anos)"
            
            if categoria.tipo == 'kids' and (idade < 13 or idade > 17):
                return False, f"Competidor com {idade} anos não pode participar da categoria Kids (13-17 anos)"
            
            if categoria.tipo == 'feminina' and competidor.sexo != 'F':
                return False, "Apenas competidoras do sexo feminino podem participar da categoria Feminina"
            
            # Validações de idade individual
            if categoria.idade_min_individual and idade < categoria.idade_min_individual:
                return False, f"Idade mínima para esta categoria é {categoria.idade_min_individual} anos"
            
            if categoria.idade_max_individual and idade > categoria.idade_max_individual:
                return False, f"Idade máxima para esta categoria é {categoria.idade_max_individual} anos"
            
            return True, "Competidor elegível para a categoria"
            
        except Exception as error:
            handle_error(error, self.validar_categoria_competidor)

    async def get_estatisticas_basicas_competidores(self):
        """Estatísticas básicas dos competidores (sem precisar de pontuação)"""
        try:
            # 1. Total de competidores por categoria
            stats_categoria = self.db.query(
                schemas.Categorias.id,
                schemas.Categorias.nome,
                schemas.Categorias.tipo,
                func.count(schemas.Competidores.id).label('total_competidores'),
                func.count(schemas.Competidores.id).filter(schemas.Competidores.ativo == True).label('competidores_ativos'),
                func.avg(schemas.Competidores.handicap).label('media_handicap'),
                func.count(schemas.Competidores.id).filter(schemas.Competidores.sexo == 'F').label('total_feminino'),
                func.count(schemas.Competidores.id).filter(schemas.Competidores.sexo == 'M').label('total_masculino')
            ).outerjoin(
                schemas.Competidores,
                schemas.Categorias.id == schemas.Competidores.categoria_id
            ).filter(
                schemas.Categorias.ativa == True
            ).group_by(
                schemas.Categorias.id,
                schemas.Categorias.nome,
                schemas.Categorias.tipo
            ).order_by(schemas.Categorias.nome).all()

            # 2. Competidores sem categoria
            sem_categoria = self.db.query(
                func.count(schemas.Competidores.id).label('total_sem_categoria'),
                func.count(schemas.Competidores.id).filter(schemas.Competidores.ativo == True).label('ativos_sem_categoria'),
                func.avg(schemas.Competidores.handicap).label('media_handicap_sem_categoria')
            ).filter(schemas.Competidores.categoria_id.is_(None)).first()

            # 3. Distribuição por handicap (GERAL - sem pontuação)
            distribuicao_handicap = self.db.query(
                schemas.Competidores.handicap,
                func.count(schemas.Competidores.id).label('quantidade'),
                func.count(schemas.Competidores.id).filter(schemas.Competidores.sexo == 'F').label('feminino'),
                func.count(schemas.Competidores.id).filter(schemas.Competidores.sexo == 'M').label('masculino')
            ).filter(
                schemas.Competidores.ativo == True
            ).group_by(
                schemas.Competidores.handicap
            ).order_by(schemas.Competidores.handicap).all()

            # 4. Distribuição por estado
            distribuicao_estado = self.db.query(
                schemas.Competidores.estado,
                func.count(schemas.Competidores.id).label('quantidade')
            ).filter(
                schemas.Competidores.ativo == True
            ).group_by(
                schemas.Competidores.estado
            ).order_by(desc('quantidade')).all()

            # 5. Distribuição por faixa etária
            hoje = date.today()
            faixas_etarias = self.db.query(
                func.case(
                    (func.extract('year', func.age(hoje, schemas.Competidores.data_nascimento)) <= 12, 'Baby (até 12)'),
                    (func.extract('year', func.age(hoje, schemas.Competidores.data_nascimento)).between(13, 17), 'Kids (13-17)'),
                    (func.extract('year', func.age(hoje, schemas.Competidores.data_nascimento)).between(18, 25), 'Jovens (18-25)'),
                    (func.extract('year', func.age(hoje, schemas.Competidores.data_nascimento)).between(26, 35), 'Adultos (26-35)'),
                    (func.extract('year', func.age(hoje, schemas.Competidores.data_nascimento)).between(36, 45), 'Veteranos (36-45)'),
                    else_='Masters (46+)'
                ).label('faixa_etaria'),
                func.count(schemas.Competidores.id).label('quantidade')
            ).filter(
                schemas.Competidores.ativo == True
            ).group_by('faixa_etaria').all()

            return {
                'por_categoria': stats_categoria,
                'sem_categoria': sem_categoria,
                'distribuicao_handicap': distribuicao_handicap,
                'distribuicao_estado': distribuicao_estado,
                'faixas_etarias': faixas_etarias,
                'resumo': {
                    'total_competidores': sum([cat.total_competidores or 0 for cat in stats_categoria]) + (sem_categoria.total_sem_categoria or 0),
                    'total_ativos': sum([cat.competidores_ativos or 0 for cat in stats_categoria]) + (sem_categoria.ativos_sem_categoria or 0),
                    'total_categorias': len(stats_categoria),
                    'handicap_mais_comum': max(distribuicao_handicap, key=lambda x: x.quantidade).handicap if distribuicao_handicap else None
                }
            }
        except Exception as error:
            handle_error(error, self.get_estatisticas_basicas_competidores)

    async def get_distribuicao_handicap_por_categoria(self, categoria_id: int):
        """Distribuição de handicap para uma categoria específica"""
        try:
            distribuicao = self.db.query(
                schemas.Competidores.handicap,
                func.count(schemas.Competidores.id).label('quantidade'),
                func.count(schemas.Competidores.id).filter(schemas.Competidores.sexo == 'F').label('feminino'),
                func.count(schemas.Competidores.id).filter(schemas.Competidores.sexo == 'M').label('masculino'),
                func.avg(func.extract('year', func.age(date.today(), schemas.Competidores.data_nascimento))).label('idade_media')
            ).filter(
                schemas.Competidores.categoria_id == categoria_id,
                schemas.Competidores.ativo == True
            ).group_by(
                schemas.Competidores.handicap
            ).order_by(schemas.Competidores.handicap).all()

            # Buscar nome da categoria
            categoria = self.db.execute(
                select(schemas.Categorias).where(schemas.Categorias.id == categoria_id)
            ).scalars().first()

            return {
                'categoria': categoria.nome if categoria else f'Categoria {categoria_id}',
                'distribuicao': distribuicao,
                'total_competidores': sum([d.quantidade for d in distribuicao]),
                'handicap_min': min([d.handicap for d in distribuicao]) if distribuicao else None,
                'handicap_max': max([d.handicap for d in distribuicao]) if distribuicao else None
            }
        except Exception as error:
            handle_error(error, self.get_distribuicao_handicap_por_categoria)

    async def get_estatisticas_trio_potencial(self, categoria_id: int):
        """Estatísticas de formação de trios potenciais"""
        try:
            # Buscar todos os competidores elegíveis
            competidores = self.buscar_para_trio(categoria_id)
            
            if len(competidores) < 3:
                return {
                    'categoria_id': categoria_id,
                    'total_competidores': len(competidores),
                    'trios_possiveis': 0,
                    'aviso': 'Menos de 3 competidores elegíveis'
                }

            # Calcular combinações possíveis
            from math import comb
            trios_possiveis = comb(len(competidores), 3)
            
            # Analisar handicaps
            handicaps = [c.handicap for c in competidores]
            
            # Analisar idades
            hoje = date.today()
            idades = []
            for c in competidores:
                idade = hoje.year - c.data_nascimento.year
                if (hoje.month, hoje.day) < (c.data_nascimento.month, c.data_nascimento.day):
                    idade -= 1
                idades.append(idade)

            return {
                'categoria_id': categoria_id,
                'total_competidores': len(competidores),
                'trios_possiveis': trios_possiveis,
                'handicap_stats': {
                    'minimo': min(handicaps),
                    'maximo': max(handicaps),
                    'media': sum(handicaps) / len(handicaps),
                    'soma_minima_trio': min(handicaps) * 3,
                    'soma_maxima_trio': max(handicaps) * 3
                },
                'idade_stats': {
                    'minima': min(idades),
                    'maxima': max(idades),
                    'media': sum(idades) / len(idades),
                    'soma_minima_trio': min(idades) * 3,
                    'soma_maxima_trio': max(idades) * 3
                },
                'distribuicao_sexo': {
                    'masculino': len([c for c in competidores if c.sexo == 'M']),
                    'feminino': len([c for c in competidores if c.sexo == 'F'])
                }
            }
        except Exception as error:
            handle_error(error, self.get_estatisticas_trio_potencial)

    async def get_dashboard_sem_pontuacao(self):
        """Dashboard básico sem precisar de pontuação"""
        try:
            # Estatísticas gerais
            estatisticas_gerais = await self.get_estatisticas_basicas_competidores()
            
            # Top 5 categorias com mais competidores
            top_categorias = sorted(
                [cat for cat in estatisticas_gerais['por_categoria'] if cat.competidores_ativos > 0],
                key=lambda x: x.competidores_ativos,
                reverse=True
            )[:5]
            
            # Estatísticas de trio para cada categoria ativa
            stats_trio_por_categoria = []
            for categoria in top_categorias:
                stats_trio = await self.get_estatisticas_trio_potencial(categoria.id)
                stats_trio_por_categoria.append(stats_trio)
            
            return {
                'resumo_geral': estatisticas_gerais['resumo'],
                'top_categorias': top_categorias,
                'distribuicao_handicap_geral': estatisticas_gerais['distribuicao_handicap'],
                'distribuicao_estados': estatisticas_gerais['distribuicao_estado'],
                'faixas_etarias': estatisticas_gerais['faixas_etarias'],
                'potencial_trios': stats_trio_por_categoria,
                'alertas': [
                    'Sistema funcionando sem dados de pontuação',
                    'Crie trios e provas para ver estatísticas completas'
                ]
            }
        except Exception as error:
            handle_error(error, self.get_dashboard_sem_pontuacao)