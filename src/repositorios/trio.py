from sqlalchemy import select, delete, update, func, desc, asc, and_, or_
from sqlalchemy.orm import Session, joinedload, aliased
from src.database import models, schemas
from src.utils.error_handler import handle_error
from src.repositorios.competidor import RepositorioCompetidor
from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any, Tuple
import pytz
import random, traceback

AMSP = pytz.timezone('America/Sao_Paulo')

class RepositorioTrio:
    
    def __init__(self, db: Session):
        self.db = db

    # ---------------------- Operações Básicas ----------------------

    async def get_by_id(self, trio_id: int):
        """Recupera um trio pelo ID com integrantes"""
        try:
            stmt = select(schemas.Trios).options(
                joinedload(schemas.Trios.integrantes).joinedload(schemas.IntegrantesTrios.competidor),
                joinedload(schemas.Trios.prova),
                joinedload(schemas.Trios.categoria),
                joinedload(schemas.Trios.resultados)
            ).where(schemas.Trios.id == trio_id)
            
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self.get_by_id)

    async def get_by_prova_categoria(self, prova_id: int, categoria_id: int):
        """Recupera trios de uma prova/categoria específica"""
        try:
            stmt = select(schemas.Trios).options(
                joinedload(schemas.Trios.integrantes).joinedload(schemas.IntegrantesTrios.competidor)
            ).where(
                schemas.Trios.prova_id == prova_id,
                schemas.Trios.categoria_id == categoria_id
            ).order_by(schemas.Trios.numero_trio)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_by_prova_categoria)

    async def post(self, trio_data: models.TrioPOST, competidores_ids: List[int]):
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

            numero_trio = trio_data.numero_trio
            if not numero_trio:
                # Buscar o maior número existente para a mesma prova/categoria
                ultimo_numero = self.db.execute(
                    select(func.max(schemas.Trios.numero_trio)).where(
                        schemas.Trios.prova_id == trio_data.prova_id,
                        schemas.Trios.categoria_id == trio_data.categoria_id
                    )
                ).scalar() or 0
                
                numero_trio = ultimo_numero + 1
            else:
                # Verificar se o número já existe na mesma prova/categoria
                numero_existente = self.db.execute(
                    select(schemas.Trios).where(
                        schemas.Trios.prova_id == trio_data.prova_id,
                        schemas.Trios.categoria_id == trio_data.categoria_id,
                        schemas.Trios.numero_trio == numero_trio
                    )
                ).scalars().first()
                
                if numero_existente:
                    raise ValueError(f"Número do trio {numero_trio} já existe nesta prova/categoria")

            # Criar o trio
            db_trio = schemas.Trios(
                prova_id=trio_data.prova_id,
                categoria_id=trio_data.categoria_id,
                status=trio_data.status,
                is_cabeca_chave=trio_data.is_cabeca_chave,
                numero_trio=numero_trio,
                formacao_manual=trio_data.formacao_manual,
                cup_type=trio_data.cup_type
            )
            
            self.db.add(db_trio)
            self.db.flush()  # Para obter o ID do trio

            # Calcular totais
            competidores = self.db.execute(
                select(schemas.Competidores).where(
                    schemas.Competidores.id.in_(competidores_ids)
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
                integrante = schemas.IntegrantesTrios(
                    trio_id=db_trio.id,
                    competidor_id=competidor_id,
                    ordem_escolha=i + 1
                )
                self.db.add(integrante)

            await self._criar_passadas_basicas(db_trio)

            self.db.commit()
            self.db.refresh(db_trio)
            
            return await self.get_by_id(db_trio.id)
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.post)

    async def _criar_passadas_basicas(self, trio: schemas.Trios):
        """Cria passadas básicas para o trio"""
        
        try:
            from src.repositorios.passadas import RepositorioPassadas
            repo_passadas = RepositorioPassadas(self.db)
            
            # Tentar configuração específica da prova/categoria
            config = repo_passadas.obter_configuracao(trio.prova_id, trio.categoria_id)
            
            if config:
                # Usar configuração específica encontrada
                max_passadas = config.max_passadas_por_trio
                tempo_limite = float(config.tempo_limite_padrao)
            else:
                # Usar configurações padrão por categoria
                categoria = self.db.execute(
                    select(schemas.Categorias).where(schemas.Categorias.id == trio.categoria_id)
                ).scalars().first()
                
                configuracoes = {
                    'baby': {'passadas': 3, 'tempo_limite': 90.0},
                    'kids': {'passadas': 5, 'tempo_limite': 75.0},
                    'mirim': {'passadas': 8, 'tempo_limite': 65.0},
                    'feminina': {'passadas': 8, 'tempo_limite': 65.0},
                    'aberta': {'passadas': 10, 'tempo_limite': 50.0},
                    'handicap': {'passadas': 10, 'tempo_limite': 55.0}
                }
                
                config_default = configuracoes.get(
                    categoria.tipo if categoria else 'aberta', 
                    configuracoes['aberta']
                )
                max_passadas = config_default['passadas']
                tempo_limite = config_default['tempo_limite']
            
            # Criar as passadas
            for numero in range(1, max_passadas + 1):
                passada = schemas.PassadasTrio(
                    trio_id=trio.id,
                    prova_id=trio.prova_id,
                    numero_passada=numero,
                    tempo_limite=tempo_limite,
                    status='pendente'
                )
                self.db.add(passada)
                
        except Exception:
            # Se der qualquer erro, criar 1 passada padrão
            passada_default = schemas.PassadasTrio(
                trio_id=trio.id,
                prova_id=trio.prova_id,
                numero_passada=1,
                tempo_limite=60.0,
                status='pendente'
            )
            self.db.add(passada_default)

    async def put(self, trio_id: int, trio_data: models.TrioPUT):
        """Atualiza um trio"""
        try:
            # Criar dicionário apenas com campos não None
            update_data = {k: v for k, v in trio_data.dict().items() if v is not None}
            update_data['updated_at'] = datetime.now(timezone.utc).astimezone(AMSP)
            
            stmt = update(schemas.Trios).where(
                schemas.Trios.id == trio_id
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
            resultado = self.db.execute(
                select(schemas.Resultados).where(schemas.Resultados.trio_id == trio_id)
            ).scalars().first()
            
            if resultado:
                raise ValueError("Não é possível excluir trio que já possui resultados")

            # Excluir integrantes primeiro (CASCADE deveria fazer isso automaticamente)
            self.db.execute(
                delete(schemas.IntegrantesTrios).where(
                    schemas.IntegrantesTrios.trio_id == trio_id
                )
            )
            
            # Excluir trio
            self.db.execute(
                delete(schemas.Trios).where(schemas.Trios.id == trio_id)
            )
            
            self.db.commit()
            return True
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.delete)

    async def reorganizar_numeracao_categoria(self, prova_id: int, categoria_id: int):
        """Reorganiza a numeração dos trios de uma categoria específica"""
        try:
            # Buscar todos os trios da prova/categoria ordenados por ID (ordem de criação)
            trios = self.db.execute(
                select(schemas.Trios).where(
                    schemas.Trios.prova_id == prova_id,
                    schemas.Trios.categoria_id == categoria_id
                ).order_by(schemas.Trios.id.asc())
            ).scalars().all()
            
            # Renumerar sequencialmente
            for i, trio in enumerate(trios, 1):
                trio.numero_trio = i
            
            self.db.commit()
            return True
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.reorganizar_numeracao_categoria)
            return False

    async def get_proximo_numero_trio(self, prova_id: int, categoria_id: int) -> int:
        """Retorna o próximo número disponível para um trio"""
        try:
            ultimo_numero = self.db.execute(
                select(func.max(schemas.Trios.numero_trio)).where(
                    schemas.Trios.prova_id == prova_id,
                    schemas.Trios.categoria_id == categoria_id
                )
            ).scalar() or 0
            
            return ultimo_numero + 1
        except Exception as error:
            handle_error(error, self.get_proximo_numero_trio)
            return 1

    # ---------------------- Sorteios ----------------------

    async def sortear_trios(self, prova_id: int, categoria_id: int, competidores_ids: List[int]) -> Dict[str, Any]:
        """
        Algoritmo baseado no script que funcionou perfeitamente
        """
        try:
            print(f"🚀 INICIANDO SORTEIO com algoritmo testado")
            print(f"📝 Competidores: {competidores_ids}")
            
            # 1. BUSCAR CONFIGURAÇÃO
            config_passadas = self.db.execute(
                select(schemas.ConfiguracaoPassadasProva).where(
                    schemas.ConfiguracaoPassadasProva.prova_id == prova_id,
                    schemas.ConfiguracaoPassadasProva.categoria_id == categoria_id,
                    schemas.ConfiguracaoPassadasProva.ativa == True
                )
            ).scalars().first()
            
            if not config_passadas:
                raise ValueError("Configuração não encontrada")

            total_participacoes = config_passadas.max_corridas_por_pessoa
            tamanho_trio = 3
            max_iter = 5000
            
            print(f"⚙️ Cada competidor pode participar {total_participacoes} vezes")
            print(f"🎯 Meta: {(len(competidores_ids) * total_participacoes) // tamanho_trio} trios máximos")

            # 2. VALIDAÇÕES BÁSICAS
            if len(competidores_ids) < tamanho_trio:
                raise ValueError("Poucos competidores para formar um trio")

            # 3. ALGORITMO PRINCIPAL (baseado no seu script)
            participacao = {}
            for comp_id in competidores_ids:
                participacao[comp_id] = 0
                
            trios_criados = []
            max_trios = (len(competidores_ids) * total_participacoes) // tamanho_trio
            numero_trio = 1
            
            # Cria uma fila dos competidores para distribuir participações de forma justa
            competidores_fila = list(competidores_ids)
            random.shuffle(competidores_fila)
            rodada = 0
            iteracoes = 0

            print(f"🔄 Iniciando formação de trios...")

            while True:
                iteracoes += 1
                if iteracoes > max_iter:
                    print(f"⚠️ Limite de {max_iter} iterações atingido! Interrompendo.")
                    break

                # Filtra só quem pode participar mais (não chegou ao limite)
                elegiveis = [comp_id for comp_id in competidores_fila if participacao[comp_id] < total_participacoes]
                
                if len(elegiveis) < tamanho_trio:
                    print(f"🔚 Não há competidores suficientes para formar mais trios")
                    print(f"   Elegíveis restantes: {len(elegiveis)}")
                    break

                # Ordena os elegíveis por quem menos jogou (prioriza quem participou menos)
                elegiveis.sort(key=lambda comp_id: participacao[comp_id])

                # Seleciona trio (priorizando quem participou menos)
                trio_candidato = elegiveis[:tamanho_trio]
                
                print(f"🔍 Trio {numero_trio}: {trio_candidato}")
                print(f"   Participações atuais: {[participacao[c] for c in trio_candidato]}")

                try:
                    # Criar trio
                    trio_data = models.TrioPOST(
                        prova_id=prova_id,
                        categoria_id=categoria_id,
                        numero_trio=numero_trio,
                        formacao_manual=False
                    )
                    
                    trio = await self.post(trio_data, trio_candidato)
                    trios_criados.append(trio)
                    
                    # Atualizar participações
                    for comp_id in trio_candidato:
                        participacao[comp_id] += 1
                    
                    print(f"✅ Trio {numero_trio} criado: {trio_candidato}")
                    print(f"   Participações atualizadas: {[participacao[c] for c in trio_candidato]}")
                    
                    numero_trio += 1
                    
                except Exception as e:
                    print(f"❌ Erro ao criar trio {trio_candidato}: {str(e)}")
                    # Em caso de erro, marca o primeiro competidor como tendo uma participação extra
                    # para evitar tentar o mesmo trio novamente
                    participacao[trio_candidato[0]] += 1

                rodada += 1
                if rodada > max_trios * 2:
                    print(f"⚠️ Limite interno de rodadas atingido! Interrompendo.")
                    break

            # 4. RELATÓRIO FINAL
            print(f"\n📊 RELATÓRIO FINAL:")
            print(f"Trios criados: {len(trios_criados)}")
            
            print(f"\n👥 Participações por competidor:")
            for comp_id in competidores_ids:
                print(f"   Competidor {comp_id}: {participacao[comp_id]} trios")
            
            faltantes = [comp_id for comp_id in competidores_ids if participacao[comp_id] < total_participacoes]
            if faltantes:
                print(f"\n⚠️ Competidores com menos participações que o desejado: {faltantes}")
            else:
                print(f"\n🎉 Todos participaram do número desejado de trios!")

            # 5. COMMIT NO BANCO
            self.db.commit()

            return {
                'trios_criados': trios_criados,
                'total_trios': len(trios_criados),
                'participacoes_por_competidor': participacao,
                'total_participacoes_realizadas': sum(participacao.values()),
                'total_participacoes_esperadas': len(competidores_ids) * total_participacoes,
                'competidores_com_deficit': faltantes,
                'eficiencia': (sum(participacao.values()) / (len(competidores_ids) * total_participacoes)) * 100,
                'mensagem': f'{len(trios_criados)} trios criados com distribuição equilibrada'
            }
            
        except Exception as error:
            self.db.rollback()
            print(f"💥 ERRO: {str(error)}")
            raise error

    def _formar_trio_sem_repeticao(self, pool_sorteio: List[int]) -> List[int]:
        """
        Forma um trio garantindo que não há competidores repetidos
        IMPORTANTE: Não modifica o pool original, apenas seleciona competidores únicos
        """
        if len(pool_sorteio) < 3:
            return []
        
        # Criar conjunto de competidores únicos disponíveis
        competidores_unicos = list(set(pool_sorteio))
        
        if len(competidores_unicos) < 3:
            return []
        
        # Embaralhar e pegar os primeiros 3
        random.shuffle(competidores_unicos)
        return competidores_unicos[:3]

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
            
            trio_data = models.TrioPOST(
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

    async def _validar_competidores_aptos(self, competidores_ids: List[int], prova_id: int, categoria_id: int) -> List[int]:
        """Valida quais competidores podem participar baseado no ControleParticipacao"""
        competidores_aptos = []
        
        for competidor_id in competidores_ids:
            # Buscar ou criar controle de participação
            controle = self.db.execute(
                select(schemas.ControleParticipacao).where(
                    schemas.ControleParticipacao.competidor_id == competidor_id,
                    schemas.ControleParticipacao.prova_id == prova_id,
                    schemas.ControleParticipacao.categoria_id == categoria_id
                )
            ).scalars().first()
            
            if not controle:
                # Criar controle se não existir
                controle = schemas.ControleParticipacao(
                    competidor_id=competidor_id,
                    prova_id=prova_id,
                    categoria_id=categoria_id,
                    total_passadas_executadas=0,
                    max_passadas_permitidas=5,  # padrão
                    pode_competir=True
                )
                self.db.add(controle)
            
            # Verificar se pode competir
            if controle.pode_competir and controle.total_passadas_executadas < controle.max_passadas_permitidas:
                competidores_aptos.append(competidor_id)
        
        self.db.commit()
        return competidores_aptos

    async def _sortear_multiplas_passadas(self, prova_id: int, categoria_id: int, competidores_aptos: List[int], 
                                    categoria, config_passadas) -> Dict[str, Any]:
        """Sorteia múltiplos trios baseado no max_passadas_por_trio"""
        
        max_passadas = config_passadas.max_passadas_por_trio
        max_corridas_pessoa = config_passadas.max_corridas_por_pessoa
        
        # Calcular quantos trios cada competidor pode participar
        participacoes_por_competidor = {}
        for comp_id in competidores_aptos:
            controle = self.db.execute(
                select(schemas.ControleParticipacao).where(
                    schemas.ControleParticipacao.competidor_id == comp_id,
                    schemas.ControleParticipacao.prova_id == prova_id,
                    schemas.ControleParticipacao.categoria_id == categoria_id
                )
            ).scalars().first()
            
            participacoes_restantes = min(
                max_corridas_pessoa - controle.total_passadas_executadas,
                max_passadas
            )
            participacoes_por_competidor[comp_id] = max(0, participacoes_restantes)
        
        # Criar pool expandido de competidores
        pool_expandido = []
        for comp_id, num_participacoes in participacoes_por_competidor.items():
            pool_expandido.extend([comp_id] * num_participacoes)
        
        if len(pool_expandido) < 3:
            raise ValueError("Não há competidores suficientes para formar trios")
        
        # Embaralhar o pool
        random.shuffle(pool_expandido)
        
        trios_criados = []
        competidores_usados_por_trio = set()
        numero_trio = 1
        
        # Formar trios garantindo que não se repitam
        while len(pool_expandido) >= 3:
            trio_atual = []
            indices_remover = []
            
            # Selecionar 3 competidores diferentes
            for i, comp_id in enumerate(pool_expandido):
                if len(trio_atual) == 3:
                    break
                    
                # Verificar se competidor já está no trio atual
                if comp_id not in [c for c in trio_atual]:
                    trio_atual.append(comp_id)
                    indices_remover.append(i)
            
            if len(trio_atual) == 3:
                # Validar trio (handicap, idade, etc.)
                repo_competidor = RepositorioCompetidor(self.db)
                valido, _ = await repo_competidor.validar_trio_handicap(trio_atual, categoria_id)
                
                if valido:
                    # Criar trio
                    trio_data = models.TrioPOST(
                        prova_id=prova_id,
                        categoria_id=categoria_id,
                        numero_trio=numero_trio,
                        formacao_manual=False
                    )
                    
                    trio = await self.post(trio_data, trio_atual)
                    trios_criados.append(trio)
                    numero_trio += 1
                    
                    # Remover competidores usados do pool (índices em ordem reversa)
                    for idx in sorted(indices_remover, reverse=True):
                        pool_expandido.pop(idx)
                else:
                    # Se trio inválido, remover apenas o primeiro competidor e tentar novamente
                    if indices_remover:
                        pool_expandido.pop(indices_remover[0])
            else:
                # Não conseguiu formar trio completo
                break
        
        return {
            'trios_criados': trios_criados,
            'total_trios': len(trios_criados),
            'competidores_sorteados': len(set([comp for trio in trios_criados for comp in trio_atual])),
            'competidores_nao_sorteados': pool_expandido,
            'max_passadas_por_trio': max_passadas,
            'max_corridas_por_pessoa': max_corridas_pessoa,
            'mensagem': f'{len(trios_criados)} trios criados com múltiplas passadas por competidor'
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
            
            trio_data = models.TrioPOST(
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
        competidores = self.db.execute(
            select(schemas.Competidores).where(
                schemas.Competidores.id.in_(competidores_ids)
            )
        ).scalars().all()
        
        # Calcular idades
        hoje = date.today()
        competidores_com_idade = []
        competidores_invalidos = []

        for c in competidores:
            if c.data_nascimento is None:
                competidores_invalidos.append(f"ID:{c.id} {c.nome} - data_nascimento é NULL")
                continue
                
            try:
                idade = hoje.year - c.data_nascimento.year
                if (hoje.month, hoje.day) < (c.data_nascimento.month, c.data_nascimento.day):
                    idade -= 1
                competidores_com_idade.append((c.id, idade))
            except Exception as e:
                competidores_invalidos.append(f"ID:{c.id} {c.nome} - erro no cálculo: {e}")
        
        if competidores_invalidos:
            raise ValueError(f"Competidores com dados inválidos: {'; '.join(competidores_invalidos)}")
        
        if len(competidores_com_idade) < 3:
            raise ValueError("Competidores insuficientes com dados válidos para formar trios")

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
                            
                            trio_data = models.TrioPOST(
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
                trio_data = models.TrioPOST(
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
                    trio_data = models.TrioPOST(
                        prova_id=prova_id,
                        categoria_id=categoria_id,
                        numero_trio=numero_trio,
                        formacao_manual=True,
                        is_cabeca_chave=True,
                        cup_type=models.TipoCopa.COPA_CAMPEOES
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
                stmt = update(schemas.IntegrantesTrios).where(
                    schemas.IntegrantesTrios.trio_id == trio_id,
                    schemas.IntegrantesTrios.competidor_id == competidor_id
                ).values(is_cabeca_chave=True)
                
                self.db.execute(stmt)
            
            self.db.commit()
        except Exception as error:
            handle_error(error, self._marcar_cabecas_chave)

    # ---------------------- Consultas e Relatórios ----------------------

    async def get_trios_prova(self, prova_id: int):
        """Lista todos os trios de uma prova"""
        try:
            stmt = select(schemas.Trios).options(
                joinedload(schemas.Trios.integrantes).joinedload(schemas.IntegrantesTrios.competidor),
                joinedload(schemas.Trios.categoria),
                joinedload(schemas.Trios.resultados)
            ).where(
                schemas.Trios.prova_id == prova_id
            ).order_by(
                schemas.Trios.categoria_id,
                schemas.Trios.numero_trio
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
                historico = self.db.execute(
                    select(
                        func.count(schemas.Pontuacao.id).label('total_provas'),
                        func.avg(schemas.Pontuacao.colocacao).label('colocacao_media'),
                        func.sum(schemas.Pontuacao.pontos_total).label('total_pontos')
                    ).where(
                        schemas.Pontuacao.competidor_id == comp.id
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
                schemas.Trios,
                schemas.Resultados.colocacao,
                schemas.Resultados.media_tempo,
                schemas.Resultados.premiacao_valor,
                schemas.Provas.nome.label('prova_nome'),
                schemas.Provas.data
            ).join(
                schemas.Resultados,
                schemas.Trios.id == schemas.Resultados.trio_id
            ).join(
                schemas.Provas,
                schemas.Trios.prova_id == schemas.Provas.id
            ).options(
                joinedload(schemas.Trios.integrantes).joinedload(schemas.IntegrantesTrios.competidor)
            ).filter(
                schemas.Trios.categoria_id == categoria_id,
                schemas.Resultados.colocacao.isnot(None)
            )

            if ano:
                query = query.filter(
                    func.extract('year', schemas.Provas.data) == ano
                )

            # Ordenar por colocação e depois por tempo médio
            query = query.order_by(
                schemas.Resultados.colocacao.asc(),
                schemas.Resultados.media_tempo.asc()
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
                inscricao_existente = self.db.execute(
                    select(schemas.IntegrantesTrios).join(
                        schemas.Trios
                    ).where(
                        schemas.Trios.prova_id == prova_id,
                        schemas.Trios.categoria_id == categoria_id,
                        schemas.IntegrantesTrios.competidor_id == comp_id
                    )
                ).scalars().first()
                
                '''if inscricao_existente:
                    competidor = self.db.execute(
                        select(schemas.Competidores).where(
                            schemas.Competidores.id == comp_id
                        )
                    ).scalars().first()
                    
                    return False, f"Competidor {competidor.nome} já está inscrito nesta prova/categoria"'''

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
                trio_data = models.TrioPOST(**trio_info['trio'])
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
                stmt = update(schemas.Trios).where(
                    schemas.Trios.id == trio.id
                ).values(numero_trio=i)
                
                self.db.execute(stmt)
            
            self.db.commit()
            return True
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.atualizar_numeros_trio)