from sqlalchemy import select, delete, update, func, desc, asc, and_, or_
from sqlalchemy.orm import Session, joinedload, aliased
from src.database import models_lctp, schemas_lctp
from src.utils.error_handler import handle_error
from src.repositorios.competidor import RepositorioCompetidor
from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any, Tuple
import pytz
import random

AMSP = pytz.timezone('America/Sao_Paulo')

class RepositorioTrio:
    
    def __init__(self, db: Session):
        self.db = db

    # ---------------------- Operações Básicas ----------------------

    async def get_by_id(self, trio_id: int):
        """Recupera um trio pelo ID com integrantes"""
        try:
            stmt = select(schemas_lctp.Trios).options(
                joinedload(schemas_lctp.Trios.integrantes).joinedload(schemas_lctp.IntegrantesTrios.competidor),
                joinedload(schemas_lctp.Trios.prova),
                joinedload(schemas_lctp.Trios.categoria),
                joinedload(schemas_lctp.Trios.resultados)
            ).where(schemas_lctp.Trios.id == trio_id)
            
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self.get_by_id)

    async def get_by_prova_categoria(self, prova_id: int, categoria_id: int):
        """Recupera trios de uma prova/categoria específica"""
        try:
            stmt = select(schemas_lctp.Trios).options(
                joinedload(schemas_lctp.Trios.integrantes).joinedload(schemas_lctp.IntegrantesTrios.competidor)
            ).where(
                schemas_lctp.Trios.prova_id == prova_id,
                schemas_lctp.Trios.categoria_id == categoria_id
            ).order_by(schemas_lctp.Trios.numero_trio)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_by_prova_categoria)

    async def post(self, trio_data: models_lctp.TrioPOST, competidores_ids: List[int]):
        """Cria um trio com seus integrantes"""
        try:
            # Validar que temos exatamente 3 competidores
            if len(competidores_ids) != 3:
                raise ValueError("Um trio deve ter exatamente 3 competidores")

            # Validar trio antes de criar
            repo_competidor = RepositorioCompetidor(self.db)
            valido, mensagem = await repo_competidor.validar_trio_handicap(
                competidores_ids, trio_data.categoria_id
            )
            
            if not valido:
                raise ValueError(mensagem)

            # Criar o trio
            db_trio = schemas_lctp.Trios(
                prova_id=trio_data.prova_id,
                categoria_id=trio_data.categoria_id,
                status=trio_data.status,
                is_cabeca_chave=trio_data.is_cabeca_chave,
                numero_trio=trio_data.numero_trio,
                formacao_manual=trio_data.formacao_manual,
                cup_type=trio_data.cup_type
            )
            
            self.db.add(db_trio)
            self.db.flush()  # Para obter o ID do trio

            # Calcular totais
            competidores = await self.db.execute(
                select(schemas_lctp.Competidores).where(
                    schemas_lctp.Competidores.id.in_(competidores_ids)
                )
            ).scalars().all()

            handicap_total = sum(c.handicap for c in competidores)
            
            # Calcular idades
            hoje = date.today()
            idade_total = 0
            for c in competidores:
                idade = hoje.year - c.data_nascimento.year
                if (hoje.month, hoje.day) < (c.data_nascimento.month, c.data_nascimento.day):
                    idade -= 1
                idade_total += idade

            db_trio.handicap_total = handicap_total
            db_trio.idade_total = idade_total

            # Criar integrantes
            for i, competidor_id in enumerate(competidores_ids):
                integrante = schemas_lctp.IntegrantesTrios(
                    trio_id=db_trio.id,
                    competidor_id=competidor_id,
                    ordem_escolha=i + 1
                )
                self.db.add(integrante)

            self.db.commit()
            self.db.refresh(db_trio)
            
            return await self.get_by_id(db_trio.id)
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.post)

    async def put(self, trio_id: int, trio_data: models_lctp.TrioPUT):
        """Atualiza um trio"""
        try:
            # Criar dicionário apenas com campos não None
            update_data = {k: v for k, v in trio_data.dict().items() if v is not None}
            update_data['updated_at'] = datetime.now(timezone.utc).astimezone(AMSP)
            
            stmt = update(schemas_lctp.Trios).where(
                schemas_lctp.Trios.id == trio_id
            ).values(**update_data)
            
            self.db.execute(stmt)
            self.db.commit()
            
            return await self.get_by_id(trio_id)
        except Exception as error:
            handle_error(error, self.put)

    async def delete(self, trio_id: int):
        """Remove um trio e seus integrantes"""
        try:
            # Verificar se o trio tem resultados
            resultado = await self.db.execute(
                select(schemas_lctp.Resultados).where(schemas_lctp.Resultados.trio_id == trio_id)
            ).scalars().first()
            
            if resultado:
                raise ValueError("Não é possível excluir trio que já possui resultados")

            # Excluir integrantes primeiro (CASCADE deveria fazer isso automaticamente)
            await self.db.execute(
                delete(schemas_lctp.IntegrantesTrios).where(
                    schemas_lctp.IntegrantesTrios.trio_id == trio_id
                )
            )
            
            # Excluir trio
            await self.db.execute(
                delete(schemas_lctp.Trios).where(schemas_lctp.Trios.id == trio_id)
            )
            
            self.db.commit()
            return True
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.delete)

    # ---------------------- Sorteios ----------------------

    async def sortear_trios(self, prova_id: int, categoria_id: int, competidores_ids: List[int]) -> Dict[str, Any]:
        """Realiza sorteio de trios baseado nas regras da categoria"""
        try:
            # Buscar categoria para verificar regras
            categoria = await self.db.execute(
                select(schemas_lctp.Categorias).where(schemas_lctp.Categorias.id == categoria_id)
            ).scalars().first()
            
            if not categoria:
                raise ValueError("Categoria não encontrada")

            if not categoria.permite_sorteio:
                raise ValueError("Esta categoria não permite sorteio")

            # Verificar número de competidores
            total_competidores = len(competidores_ids)
            
            if total_competidores < 3:
                raise ValueError("Número insuficiente de competidores para formar trios")

            # Aplicar regras de sorteio por tipo de categoria
            if categoria.tipo.value == 'baby':
                return await self._sortear_completo(prova_id, categoria_id, competidores_ids)
            elif categoria.tipo.value in ['kids', 'feminina']:
                return await self._sortear_parcial(prova_id, categoria_id, competidores_ids, categoria)
            elif categoria.tipo.value == 'mirim':
                return await self._sortear_mirim(prova_id, categoria_id, competidores_ids, categoria)
            else:
                return await self._sortear_aberto(prova_id, categoria_id, competidores_ids, categoria)
                
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.sortear_trios)

    async def _sortear_completo(self, prova_id: int, categoria_id: int, competidores_ids: List[int]) -> Dict[str, Any]:
        """Sorteio completo para categoria baby"""
        competidores = competidores_ids.copy()
        random.shuffle(competidores)
        
        trios_criados = []
        competidores_sorteados = []
        numero_trio = 1
        
        # Formar trios de 3 em 3
        for i in range(0, len(competidores) - 2, 3):
            trio_competidores = competidores[i:i+3]
            
            trio_data = models_lctp.TrioPOST(
                prova_id=prova_id,
                categoria_id=categoria_id,
                numero_trio=numero_trio,
                formacao_manual=False
            )
            
            trio = await self.post(trio_data, trio_competidores)
            trios_criados.append(trio)
            competidores_sorteados.extend(trio_competidores)
            numero_trio += 1

        competidores_nao_sorteados = [c for c in competidores_ids if c not in competidores_sorteados]
        
        return {
            'trios_criados': trios_criados,
            'total_trios': len(trios_criados),
            'competidores_sorteados': len(competidores_sorteados),
            'competidores_nao_sorteados': competidores_nao_sorteados,
            'mensagem': f'{len(trios_criados)} trios criados por sorteio completo'
        }

    async def _sortear_parcial(self, prova_id: int, categoria_id: int, competidores_ids: List[int], categoria) -> Dict[str, Any]:
        """Sorteio parcial para kids e feminina"""
        total_competidores = len(competidores_ids)
        
        # Determinar quantos competidores sortear
        min_sorteio = categoria.min_inscricoes_sorteio or 3
        max_sorteio = categoria.max_inscricoes_sorteio or 9
        
        num_sortear = min(max_sorteio, total_competidores)
        num_sortear = max(min_sorteio, num_sortear)
        
        # Garantir múltiplo de 3
        num_sortear = (num_sortear // 3) * 3
        
        if num_sortear == 0:
            raise ValueError("Número insuficiente de competidores para sorteio")
        # Selecionar competidores aleatoriamente
        competidores_selecionados = random.sample(competidores_ids, num_sortear)
        random.shuffle(competidores_selecionados)
        
        trios_criados = []
        competidores_sorteados = []
        numero_trio = 1
        
        # Formar trios de 3 em 3
        for i in range(0, len(competidores_selecionados), 3):
            trio_competidores = competidores_selecionados[i:i+3]
            
            trio_data = models_lctp.TrioPOST(
                prova_id=prova_id,
                categoria_id=categoria_id,
                numero_trio=numero_trio,
                formacao_manual=False
            )
            
            trio = await self.post(trio_data, trio_competidores)
            trios_criados.append(trio)
            competidores_sorteados.extend(trio_competidores)
            numero_trio += 1

        competidores_nao_sorteados = [c for c in competidores_ids if c not in competidores_sorteados]
        
        return {
            'trios_criados': trios_criados,
            'total_trios': len(trios_criados),
            'competidores_sorteados': len(competidores_sorteados),
            'competidores_nao_sorteados': competidores_nao_sorteados,
            'mensagem': f'{len(trios_criados)} trios criados por sorteio parcial'
        }

    async def _sortear_mirim(self, prova_id: int, categoria_id: int, competidores_ids: List[int], categoria) -> Dict[str, Any]:
        """Sorteio para categoria mirim com restrição de idade"""
        repo_competidor = RepositorioCompetidor(self.db)
        
        # Buscar dados dos competidores
        competidores = await self.db.execute(
            select(schemas_lctp.Competidores).where(
                schemas_lctp.Competidores.id.in_(competidores_ids)
            )
        ).scalars().all()
        
        # Calcular idades
        hoje = date.today()
        competidores_com_idade = []
        for c in competidores:
            idade = hoje.year - c.data_nascimento.year
            if (hoje.month, hoje.day) < (c.data_nascimento.month, c.data_nascimento.day):
                idade -= 1
            competidores_com_idade.append((c.id, idade))
        
        # Ordenar por idade para facilitar combinações
        competidores_com_idade.sort(key=lambda x: x[1])
        
        trios_criados = []
        competidores_usados = set()
        numero_trio = 1
        idade_max = categoria.idade_max_trio or 36
        
        # Algoritmo para formar trios respeitando limite de idade
        tentativas = 0
        max_tentativas = 1000
        
        while len([c for c in competidores_com_idade if c[0] not in competidores_usados]) >= 3 and tentativas < max_tentativas:
            disponivel = [c for c in competidores_com_idade if c[0] not in competidores_usados]
            
            # Tentar formar trio começando com o mais novo
            for i, (id1, idade1) in enumerate(disponivel):
                for j, (id2, idade2) in enumerate(disponivel[i+1:], i+1):
                    for k, (id3, idade3) in enumerate(disponivel[j+1:], j+1):
                        if idade1 + idade2 + idade3 <= idade_max:
                            # Trio válido encontrado
                            trio_competidores = [id1, id2, id3]
                            
                            trio_data = models_lctp.TrioPOST(
                                prova_id=prova_id,
                                categoria_id=categoria_id,
                                numero_trio=numero_trio,
                                formacao_manual=False
                            )
                            
                            trio = await self.post(trio_data, trio_competidores)
                            trios_criados.append(trio)
                            competidores_usados.update(trio_competidores)
                            numero_trio += 1
                            break
                    else:
                        continue
                    break
                else:
                    continue
                break
            else:
                # Não conseguiu formar mais trios válidos
                break
                
            tentativas += 1

        competidores_nao_sorteados = [c[0] for c in competidores_com_idade if c[0] not in competidores_usados]
        
        return {
            'trios_criados': trios_criados,
            'total_trios': len(trios_criados),
            'competidores_sorteados': len(competidores_usados),
            'competidores_nao_sorteados': competidores_nao_sorteados,
            'mensagem': f'{len(trios_criados)} trios criados respeitando limite de idade'
        }

    async def _sortear_aberto(self, prova_id: int, categoria_id: int, competidores_ids: List[int], categoria) -> Dict[str, Any]:
        """Sorteio para categorias abertas"""
        # Similar ao sorteio completo, mas com possíveis restrições de handicap
        competidores = competidores_ids.copy()
        random.shuffle(competidores)
        
        trios_criados = []
        competidores_sorteados = []
        numero_trio = 1
        repo_competidor = RepositorioCompetidor(self.db)
        
        # Tentar formar trios validando as regras
        i = 0
        while i <= len(competidores) - 3:
            trio_candidato = competidores[i:i+3]
            
            # Validar trio
            valido, _ = await repo_competidor.validar_trio_handicap(trio_candidato, categoria.id)
            
            if valido:
                trio_data = models_lctp.TrioPOST(
                    prova_id=prova_id,
                    categoria_id=categoria_id,
                    numero_trio=numero_trio,
                    formacao_manual=False
                )
                
                trio = await self.post(trio_data, trio_candidato)
                trios_criados.append(trio)
                competidores_sorteados.extend(trio_candidato)
                numero_trio += 1
                i += 3  # Próximo trio
            else:
                # Reembaralhar e tentar novamente
                restantes = competidores[i:]
                random.shuffle(restantes)
                competidores = competidores[:i] + restantes
                i += 1  # Tentar próxima combinação

        competidores_nao_sorteados = [c for c in competidores_ids if c not in competidores_sorteados]
        
        return {
            'trios_criados': trios_criados,
            'total_trios': len(trios_criados),
            'competidores_sorteados': len(competidores_sorteados),
            'competidores_nao_sorteados': competidores_nao_sorteados,
            'mensagem': f'{len(trios_criados)} trios criados por sorteio aberto'
        }

    # ---------------------- Copa dos Campeões ----------------------

    async def criar_trios_copa_campeoes(self, prova_id: int, categoria_id: int, campeoes_handicap: List[Dict]) -> Dict[str, Any]:
        """Cria trios para Copa dos Campeões com cabeças de chave"""
        try:
            # campeoes_handicap = [{'handicap': 0, 'competidor_id': 1}, ...]
            
            if len(campeoes_handicap) < 3:
                raise ValueError("Necessário pelo menos 3 campeões para formar trios da Copa dos Campeões")

            # Organizar cabeças de chave por handicap
            cabecas_chave = {}
            for campeao in campeoes_handicap:
                handicap = campeao['handicap']
                if handicap not in cabecas_chave:
                    cabecas_chave[handicap] = []
                cabecas_chave[handicap].append(campeao['competidor_id'])

            # Ordem de escolha: iniciante(0), 1, 2, 3, 4, 5, 7
            ordem_handicap = [0, 1, 2, 3, 4, 5, 7]
            
            trios_criados = []
            numero_trio = 1
            competidores_usados = set()

            # Distribuir cabeças de chave entre trios
            max_trios = min(len(campeoes_handicap) // 3, 10)  # Máximo 10 trios
            
            for trio_num in range(max_trios):
                trio_competidores = []
                
                # Selecionar cabeças de chave seguindo ordem de handicap
                for handicap in ordem_handicap:
                    if len(trio_competidores) >= 3:
                        break
                        
                    if handicap in cabecas_chave:
                        disponiveis = [c for c in cabecas_chave[handicap] if c not in competidores_usados]
                        if disponiveis:
                            escolhido = disponiveis[0]  # Primeiro disponível
                            trio_competidores.append(escolhido)
                            competidores_usados.add(escolhido)
                
                # Se não conseguiu 3, completar com os restantes
                if len(trio_competidores) < 3:
                    restantes = [c['competidor_id'] for c in campeoes_handicap if c['competidor_id'] not in competidores_usados]
                    while len(trio_competidores) < 3 and restantes:
                        trio_competidores.append(restantes.pop(0))
                        competidores_usados.add(trio_competidores[-1])

                if len(trio_competidores) == 3:
                    trio_data = models_lctp.TrioPOST(
                        prova_id=prova_id,
                        categoria_id=categoria_id,
                        numero_trio=numero_trio,
                        formacao_manual=True,
                        is_cabeca_chave=True,
                        cup_type=models_lctp.TipoCopa.COPA_CAMPEOES
                    )
                    
                    trio = await self.post(trio_data, trio_competidores)
                    
                    # Marcar cabeças de chave nos integrantes
                    await self._marcar_cabecas_chave(trio.id, trio_competidores)
                    
                    trios_criados.append(trio)
                    numero_trio += 1

            competidores_nao_usados = [c['competidor_id'] for c in campeoes_handicap if c['competidor_id'] not in competidores_usados]
            
            return {
                'trios_criados': trios_criados,
                'total_trios': len(trios_criados),
                'competidores_usados': len(competidores_usados),
                'competidores_nao_usados': competidores_nao_usados,
                'mensagem': f'{len(trios_criados)} trios da Copa dos Campeões criados'
            }
            
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.criar_trios_copa_campeoes)

    async def _marcar_cabecas_chave(self, trio_id: int, competidores_ids: List[int]):
        """Marca os primeiros competidores como cabeças de chave"""
        try:
            # Marcar os 2 primeiros como cabeças de chave (ou conforme regra específica)
            for i, competidor_id in enumerate(competidores_ids[:2]):  # Primeiros 2
                stmt = update(schemas_lctp.IntegrantesTrios).where(
                    schemas_lctp.IntegrantesTrios.trio_id == trio_id,
                    schemas_lctp.IntegrantesTrios.competidor_id == competidor_id
                ).values(is_cabeca_chave=True)
                
                self.db.execute(stmt)
            
            self.db.commit()
        except Exception as error:
            handle_error(error, self._marcar_cabecas_chave)

    # ---------------------- Consultas e Relatórios ----------------------

    async def get_trios_prova(self, prova_id: int):
        """Lista todos os trios de uma prova"""
        try:
            stmt = select(schemas_lctp.Trios).options(
                joinedload(schemas_lctp.Trios.integrantes).joinedload(schemas_lctp.IntegrantesTrios.competidor),
                joinedload(schemas_lctp.Trios.categoria),
                joinedload(schemas_lctp.Trios.resultados)
            ).where(
                schemas_lctp.Trios.prova_id == prova_id
            ).order_by(
                schemas_lctp.Trios.categoria_id,
                schemas_lctp.Trios.numero_trio
            )
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_trios_prova)

    async def get_estatisticas_trio(self, trio_id: int):
        """Recupera estatísticas de um trio específico"""
        try:
            trio = await self.get_by_id(trio_id)
            if not trio:
                return None

            # Estatísticas dos integrantes
            estatisticas_integrantes = []
            for integrante in trio.integrantes:
                comp = integrante.competidor
                
                # Histórico do competidor
                historico = await self.db.execute(
                    select(
                        func.count(schemas_lctp.Pontuacao.id).label('total_provas'),
                        func.avg(schemas_lctp.Pontuacao.colocacao).label('colocacao_media'),
                        func.sum(schemas_lctp.Pontuacao.pontos_total).label('total_pontos')
                    ).where(
                        schemas_lctp.Pontuacao.competidor_id == comp.id
                    )
                ).first()
                
                estatisticas_integrantes.append({
                    'competidor': comp,
                    'total_provas': historico.total_provas or 0,
                    'colocacao_media': float(historico.colocacao_media) if historico.colocacao_media else None,
                    'total_pontos': float(historico.total_pontos) if historico.total_pontos else 0
                })

            # Resultado do trio se disponível
            resultado_trio = None
            if trio.resultados:
                resultado_trio = {
                    'colocacao': trio.resultados.colocacao,
                    'media_tempo': trio.resultados.media_tempo,
                    'premiacao': trio.resultados.premiacao_valor,
                    'no_time': trio.resultados.no_time
                }

            return {
                'trio': trio,
                'estatisticas_integrantes': estatisticas_integrantes,
                'resultado': resultado_trio,
                'total_handicap': trio.handicap_total,
                'total_idade': trio.idade_total
            }
            
        except Exception as error:
            handle_error(error, self.get_estatisticas_trio)

    async def get_ranking_trios_categoria(self, categoria_id: int, ano: Optional[int] = None):
        """Gera ranking de trios por categoria"""
        try:
            query = self.db.query(
                schemas_lctp.Trios,
                schemas_lctp.Resultados.colocacao,
                schemas_lctp.Resultados.media_tempo,
                schemas_lctp.Resultados.premiacao_valor,
                schemas_lctp.Provas.nome.label('prova_nome'),
                schemas_lctp.Provas.data
            ).join(
                schemas_lctp.Resultados,
                schemas_lctp.Trios.id == schemas_lctp.Resultados.trio_id
            ).join(
                schemas_lctp.Provas,
                schemas_lctp.Trios.prova_id == schemas_lctp.Provas.id
            ).options(
                joinedload(schemas_lctp.Trios.integrantes).joinedload(schemas_lctp.IntegrantesTrios.competidor)
            ).filter(
                schemas_lctp.Trios.categoria_id == categoria_id,
                schemas_lctp.Resultados.colocacao.isnot(None)
            )

            if ano:
                query = query.filter(
                    func.extract('year', schemas_lctp.Provas.data) == ano
                )

            # Ordenar por colocação e depois por tempo médio
            query = query.order_by(
                schemas_lctp.Resultados.colocacao.asc(),
                schemas_lctp.Resultados.media_tempo.asc()
            )

            return query.all()
        except Exception as error:
            handle_error(error, self.get_ranking_trios_categoria)

    # ---------------------- Validações ----------------------

    async def validar_inscricao_trio(self, prova_id: int, categoria_id: int, competidores_ids: List[int]):
        """Valida se um trio pode ser inscrito em uma prova/categoria"""
        try:
            # Verificar se já existem competidores inscritos nesta prova/categoria
            for comp_id in competidores_ids:
                inscricao_existente = await self.db.execute(
                    select(schemas_lctp.IntegrantesTrios).join(
                        schemas_lctp.Trios
                    ).where(
                        schemas_lctp.Trios.prova_id == prova_id,
                        schemas_lctp.Trios.categoria_id == categoria_id,
                        schemas_lctp.IntegrantesTrios.competidor_id == comp_id
                    )
                ).scalars().first()
                
                if inscricao_existente:
                    competidor = await self.db.execute(
                        select(schemas_lctp.Competidores).where(
                            schemas_lctp.Competidores.id == comp_id
                        )
                    ).scalars().first()
                    
                    return False, f"Competidor {competidor.nome} já está inscrito nesta prova/categoria"

            # Validar regras do trio
            repo_competidor = RepositorioCompetidor(self.db)
            valido, mensagem = await repo_competidor.validar_trio_handicap(competidores_ids, categoria_id)
            
            return valido, mensagem
            
        except Exception as error:
            handle_error(error, self.validar_inscricao_trio)

    # ---------------------- Operações em Lote ----------------------

    async def criar_multiplos_trios(self, trios_data: List[Dict[str, Any]]):
        """Cria múltiplos trios em uma transação"""
        try:
            trios_criados = []
            
            for trio_info in trios_data:
                trio_data = models_lctp.TrioPOST(**trio_info['trio'])
                competidores_ids = trio_info['competidores_ids']
                
                trio = await self.post(trio_data, competidores_ids)
                trios_criados.append(trio)
            
            return trios_criados
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.criar_multiplos_trios)

    async def atualizar_numeros_trio(self, prova_id: int, categoria_id: int):
        """Reorganiza numeração dos trios de uma prova/categoria"""
        try:
            trios = await self.get_by_prova_categoria(prova_id, categoria_id)
            
            for i, trio in enumerate(trios, 1):
                stmt = update(schemas_lctp.Trios).where(
                    schemas_lctp.Trios.id == trio.id
                ).values(numero_trio=i)
                
                self.db.execute(stmt)
            
            self.db.commit()
            return True
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.atualizar_numeros_trio)