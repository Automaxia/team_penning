from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc, asc, text
from typing import List, Optional, Dict, Any, Tuple, overload, Union
from datetime import datetime, timedelta
import json
from decimal import Decimal

from src.database.schemas import (
    PassadasTrio, ConfiguracaoPassadasProva, ControleParticipacao,
    Trios, Competidores, Provas, Categorias, IntegrantesTrios, Resultados
)
from src.database.models import (
    PassadaTrioPOST, PassadaTrioPUT, ConfiguracaoPassadasPOST, ConfiguracaoPassadasPUT,
    FiltrosPassadas, FiltrosControleParticipacao, StatusPassada, RegistrarTempoRequest,
    CriarPassadasLoteRequest, ValidarPassadaRequest, ValidacaoPassadaResponse
)

class RepositorioPassadas:
    """Repositório para operações com passadas de trios"""
    
    def __init__(self, db: Session):
        self.db = db

    # ----- CRUD Passadas -----
    
    def criar_passada(self, passada_data: PassadaTrioPOST) -> PassadasTrio:
        """Cria uma nova passada"""
        # Validar se trio existe e pode criar passada
        trio = self.db.query(Trios).filter(Trios.id == passada_data.trio_id).first()
        if not trio:
            raise ValueError(f"Trio {passada_data.trio_id} não encontrado")
        
        # Verificar se número da passada já existe para este trio
        passada_existente = self.db.query(PassadasTrio).filter(
            and_(
                PassadasTrio.trio_id == passada_data.trio_id,
                PassadasTrio.numero_passada == passada_data.numero_passada
            )
        ).first()
        
        if passada_existente:
            raise ValueError(f"Passada {passada_data.numero_passada} já existe para este trio")
        
        # Validar configuração da prova
        config = self._obter_configuracao_prova(trio.prova_id, trio.categoria_id)
        if config and passada_data.numero_passada > config.max_passadas_por_trio:
            raise ValueError(f"Número de passada excede o máximo permitido ({config.max_passadas_por_trio})")
        
        # Criar passada
        nova_passada = PassadasTrio(**passada_data.dict())
        
        # Definir tempo limite se não informado
        if not nova_passada.tempo_limite and config:
            nova_passada.tempo_limite = config.tempo_limite_padrao
        
        self.db.add(nova_passada)
        self.db.commit()
        self.db.refresh(nova_passada)
        
        return nova_passada
    
    def obter_passada(self, passada_id: int) -> Optional[PassadasTrio]:
        """Obtém uma passada pelo ID"""
        return self.db.query(PassadasTrio).options(
            joinedload(PassadasTrio.trio).joinedload(Trios.integrantes).joinedload(IntegrantesTrios.competidor),
            joinedload(PassadasTrio.prova),
            joinedload(PassadasTrio.trio).joinedload(Trios.categoria)
        ).filter(PassadasTrio.id == passada_id).first()
    
    def atualizar_passada(self, passada_id: int, passada_data: PassadaTrioPUT) -> Optional[PassadasTrio]:
        """Atualiza uma passada"""
        passada = self.db.query(PassadasTrio).filter(PassadasTrio.id == passada_id).first()
        if not passada:
            return None
        
        # ✅ VERIFICAR SAT: Não permitir alteração se for SAT (exceto para remover SAT)
        if passada.is_sat and not hasattr(passada_data, 'remover_sat'):
            raise ValueError("Não é possível alterar passada com SAT aplicado. Use o endpoint específico para remover SAT.")
        
        # Atualizar campos fornecidos
        for campo, valor in passada_data.dict(exclude_unset=True).items():
            setattr(passada, campo, valor)
        
        # Auto-calcular pontos se tempo foi informado
        if passada_data.tempo_realizado is not None and passada.tempo_limite and not passada.is_sat:
            passada.pontos_passada = self._calcular_pontos_tempo(
                passada_data.tempo_realizado, passada.tempo_limite
            )
            
            # Auto-determinar status
            if passada_data.tempo_realizado > passada.tempo_limite:
                passada.status = StatusPassada.NO_TIME
            else:
                passada.status = StatusPassada.EXECUTADA
            
            # ✅ NOVO: Calcular colocação automaticamente
            passada.colocacao_passada = self._calcular_colocacao_passada(passada)
        
        passada.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(passada)
        
        # ✅ ATUALIZAR COLOCAÇÕES RELACIONADAS se houve mudança de tempo
        if passada_data.tempo_realizado is not None and not passada.is_sat:
            self._atualizar_colocacoes_relacionadas(passada)
        
        return passada
    
    def deletar_passada(self, passada_id: int) -> bool:
        """Deleta uma passada"""
        passada = self.db.query(PassadasTrio).filter(PassadasTrio.id == passada_id).first()
        if not passada:
            return False
        
        self.db.delete(passada)
        self.db.commit()
        return True
    
    def listar_passadas(self, filtros: FiltrosPassadas) -> Tuple[List[PassadasTrio], int]:
        """Lista passadas com SELECT puro - SIMPLES E DIRETO"""
        
        # SELECT com JOIN para pegar todos os dados de uma vez
        query_sql = """
        SELECT 
            p.id,
            p.trio_id,
            p.prova_id,
            p.numero_passada,
            p.numero_boi,
            p.tempo_realizado,
            p.tempo_limite,
            p.status,
            p.observacoes,
            p.pontos_passada,
            p.colocacao_passada,
            p.data_hora_passada,
            p.created_at,
            p.updated_at,
            
            -- ✅ NOVOS CAMPOS SAT
            p.is_sat,
            p.motivo_sat,
            p.desclassificado_por,
            p.data_sat,
            
            -- Dados do trio
            t.numero_trio,
            t.handicap_total,
            t.idade_total,
            
            -- Dados da categoria
            c.id as categoria_id,
            c.nome as categoria_nome,
            c.tipo as categoria_tipo,
            
            -- Dados da prova
            pr.nome as prova_nome,
            pr.data as prova_data,
            
            -- Competidores (concatenados)
            STRING_AGG(comp.nome, ', ' ORDER BY it.ordem_escolha) as competidores_nomes,
            STRING_AGG(CAST(comp.id AS VARCHAR), ',' ORDER BY it.ordem_escolha) as competidores_ids,
            STRING_AGG(CAST(comp.handicap AS VARCHAR), ',' ORDER BY it.ordem_escolha) as competidores_handicaps
            
        FROM passadas_trio p
        LEFT JOIN trios t ON p.trio_id = t.id
        LEFT JOIN categorias c ON t.categoria_id = c.id  
        LEFT JOIN provas pr ON p.prova_id = pr.id
        LEFT JOIN integrantes_trios it ON t.id = it.trio_id
        LEFT JOIN competidores comp ON it.competidor_id = comp.id
        
        WHERE 1=1
        """
        
        params = {}
        
        # Aplicar filtros existentes
        if filtros.trio_id:
            query_sql += " AND p.trio_id = :trio_id"
            params['trio_id'] = filtros.trio_id
        
        if filtros.prova_id:
            query_sql += " AND p.prova_id = :prova_id"
            params['prova_id'] = filtros.prova_id
        
        if filtros.categoria_id:
            query_sql += " AND t.categoria_id = :categoria_id"
            params['categoria_id'] = filtros.categoria_id
        
        if filtros.numero_passada:
            query_sql += " AND p.numero_passada = :numero_passada"
            params['numero_passada'] = filtros.numero_passada
        
        if filtros.status:
            query_sql += " AND p.status = :status"
            params['status'] = filtros.status
        
        if filtros.numero_boi:
            query_sql += " AND p.numero_boi = :numero_boi"
            params['numero_boi'] = filtros.numero_boi
        
        if filtros.apenas_executadas:
            query_sql += " AND p.status = 'executada'"
        
        # ✅ NOVOS FILTROS SAT
        if hasattr(filtros, 'apenas_sat') and filtros.apenas_sat:
            query_sql += " AND p.is_sat = true"
        
        if hasattr(filtros, 'excluir_sat') and filtros.excluir_sat:
            query_sql += " AND (p.is_sat = false OR p.is_sat IS NULL)"
        
        if hasattr(filtros, 'apenas_validas_ranking') and filtros.apenas_validas_ranking:
            query_sql += " AND (p.is_sat = false OR p.is_sat IS NULL) AND p.status IN ('executada', 'no_time')"
        
        # GROUP BY para o STRING_AGG funcionar
        query_sql += """
        GROUP BY 
            p.id, p.trio_id, p.prova_id, p.numero_passada, p.numero_boi,
            p.tempo_realizado, p.tempo_limite, p.status, p.observacoes,
            p.pontos_passada, p.colocacao_passada, p.data_hora_passada,
            p.created_at, p.updated_at,
            p.is_sat, p.motivo_sat, p.desclassificado_por, p.data_sat,
            t.numero_trio, t.handicap_total, t.idade_total,
            c.id, c.nome, c.tipo, pr.nome, pr.data
        """
        
        # ✅ ORDENAÇÃO CORRIGIDA - SQL PURO
        query_sql += """
        ORDER BY 
            CASE WHEN p.data_hora_passada IS NOT NULL THEN 1 ELSE 0 END,
            p.colocacao_passada ASC NULLS LAST,
            p.tempo_realizado ASC NULLS LAST
        """

        # Contar total (query separada mais simples)
        count_sql = "SELECT COUNT(DISTINCT p.id) FROM passadas_trio p LEFT JOIN trios t ON p.trio_id = t.id WHERE 1=1"
        
        if filtros.trio_id:
            count_sql += " AND p.trio_id = :trio_id"
        if filtros.prova_id:
            count_sql += " AND p.prova_id = :prova_id"
        if filtros.categoria_id:
            count_sql += " AND t.categoria_id = :categoria_id"
        if filtros.numero_passada:
            count_sql += " AND p.numero_passada = :numero_passada"
        if filtros.status:
            count_sql += " AND p.status = :status"
        if filtros.numero_boi:
            count_sql += " AND p.numero_boi = :numero_boi"
        if filtros.apenas_executadas:
            count_sql += " AND p.status = 'executada'"
        
        # ✅ FILTROS SAT NO COUNT
        if hasattr(filtros, 'apenas_sat') and filtros.apenas_sat:
            count_sql += " AND p.is_sat = true"
        if hasattr(filtros, 'excluir_sat') and filtros.excluir_sat:
            count_sql += " AND (p.is_sat = false OR p.is_sat IS NULL)"

        # Executar contagem
        total = self.db.execute(text(count_sql), params).scalar()
        
        # Executar query principal
        result = self.db.execute(text(query_sql), params).fetchall()
        
        # Converter para lista de dicionários
        passadas = []
        for row in result:
            # Processar competidores
            competidores = []
            if row.competidores_nomes:
                nomes = row.competidores_nomes.split(', ')
                ids = row.competidores_ids.split(',') if row.competidores_ids else []
                handicaps = row.competidores_handicaps.split(',') if row.competidores_handicaps else []
                
                for i, nome in enumerate(nomes):
                    competidores.append({
                        'id': int(ids[i]) if i < len(ids) else None,
                        'nome': nome,
                        'handicap': int(handicaps[i]) if i < len(handicaps) else None
                    })
            
            passada = {
                'id': row.id,
                'trio_id': row.trio_id,
                'prova_id': row.prova_id,
                'numero_passada': row.numero_passada,
                'numero_boi': row.numero_boi,
                'tempo_realizado': float(row.tempo_realizado) if row.tempo_realizado else None,
                'tempo_limite': float(row.tempo_limite),
                'status': row.status,
                'observacoes': row.observacoes,
                'pontos_passada': float(row.pontos_passada),
                'colocacao_passada': row.colocacao_passada,
                'data_hora_passada': row.data_hora_passada.isoformat() if row.data_hora_passada else None,
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None,
                
                # ✅ NOVOS CAMPOS SAT
                'is_sat': row.is_sat or False,
                'motivo_sat': row.motivo_sat,
                'desclassificado_por': row.desclassificado_por,
                'data_sat': row.data_sat.isoformat() if row.data_sat else None,
                
                # ✅ CAMPOS CALCULADOS SAT
                'valida_para_ranking': not (row.is_sat or False),
                'status_descricao': self._obter_status_descricao(row.status, row.is_sat),
                
                # ✅ DADOS QUE VOCÊ QUERIA
                'trio': {
                    'numero_trio': row.numero_trio,
                    'handicap_total': row.handicap_total,
                    'idade_total': row.idade_total,
                    'categoria': {
                        'id': row.categoria_id,
                        'nome': row.categoria_nome,
                        'tipo': row.categoria_tipo
                    },
                    'integrantes': competidores
                },
                'prova': {
                    'nome': row.prova_nome,
                    'data': row.prova_data.isoformat() if row.prova_data else None
                }
            }
            
            passadas.append(passada)
        
        return passadas, total
    
    # ----- Operações em Lote -----
    
    def criar_passadas_lote(self, request: CriarPassadasLoteRequest) -> List[PassadasTrio]:
        """Cria múltiplas passadas para um trio"""
        trio = self.db.query(Trios).filter(Trios.id == request.trio_id).first()
        if not trio:
            raise ValueError(f"Trio {request.trio_id} não encontrado")
        
        config = self._obter_configuracao_prova(trio.prova_id, trio.categoria_id)
        
        # Validar quantidade
        if config and request.quantidade_passadas > config.max_passadas_por_trio:
            raise ValueError(f"Quantidade excede máximo permitido ({config.max_passadas_por_trio})")
        
        # Obter próximo número de passada
        if request.auto_numerar:
            ultima_passada = self.db.query(func.max(PassadasTrio.numero_passada)).filter(
                PassadasTrio.trio_id == request.trio_id
            ).scalar() or 0
            proximo_numero = ultima_passada + 1
        else:
            proximo_numero = 1
        
        passadas_criadas = []
        
        for i in range(request.quantidade_passadas):
            passada_data = {
                'trio_id': request.trio_id,
                'prova_id': trio.prova_id,
                'numero_passada': proximo_numero + i,
                'tempo_limite': request.tempo_limite or (config.tempo_limite_padrao if config else 60.0),
                'status': StatusPassada.PENDENTE
            }
            
            # Boi predefinido se fornecido
            if request.bois_predefinidos and i < len(request.bois_predefinidos):
                passada_data['numero_boi'] = request.bois_predefinidos[i]
            
            nova_passada = PassadasTrio(**passada_data)
            self.db.add(nova_passada)
            passadas_criadas.append(nova_passada)
        
        self.db.commit()
        
        for passada in passadas_criadas:
            self.db.refresh(passada)
        
        return passadas_criadas
    
    def registrar_tempo(self, request: RegistrarTempoRequest) -> PassadasTrio:
        """Registra tempo de uma passada"""
        passada = self.db.query(PassadasTrio).filter(PassadasTrio.id == request.passada_id).first()
        if not passada:
            raise ValueError(f"Passada {request.passada_id} não encontrada")
        
        # ✅ VERIFICAR SAT: Não permitir registrar tempo se for SAT
        if passada.is_sat:
            raise ValueError("Não é possível registrar tempo em passada com SAT aplicado")
        
        # Atualizar dados
        passada.tempo_realizado = request.tempo_realizado
        passada.data_hora_passada = datetime.now()
        
        if request.numero_boi:
            passada.numero_boi = request.numero_boi
        
        if request.observacoes:
            passada.observacoes = request.observacoes
        
        # Determinar status
        if request.tempo_realizado > passada.tempo_limite:
            passada.status = StatusPassada.NO_TIME
        else:
            passada.status = StatusPassada.EXECUTADA
        
        # Calcular pontos se solicitado
        if request.calcular_pontos:
            passada.pontos_passada = self._calcular_pontos_tempo(
                request.tempo_realizado, passada.tempo_limite
            )
        
        # ✅ NOVO: Calcular colocação automaticamente
        passada.colocacao_passada = self._calcular_colocacao_passada(passada)
        
        passada.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(passada)
        
        # ✅ NOVO: Atualizar colocações de outras passadas se necessário
        self._atualizar_colocacoes_relacionadas(passada)
        
        return passada
    
    # ----- Métodos SAT -----
    
    def aplicar_sat_passada(self, passada_id: int, motivo: str, aplicado_por: str = None) -> PassadasTrio:
        """Aplica SAT em uma passada e recalcula colocações"""
        
        passada = self.db.query(PassadasTrio).filter(PassadasTrio.id == passada_id).first()
        if not passada:
            raise ValueError(f"Passada {passada_id} não encontrada")
        
        # Aplicar SAT usando método do schema
        passada.aplicar_sat(motivo, aplicado_por)
        
        # Remover da colocação
        passada.colocacao_passada = None
        
        self.db.commit()
        self.db.refresh(passada)
        
        # Recalcular colocações das passadas relacionadas
        self._atualizar_colocacoes_relacionadas(passada)
        
        return passada

    def remover_sat_passada(self, passada_id: int) -> PassadasTrio:
        """Remove SAT de uma passada e recalcula colocações"""
        
        passada = self.db.query(PassadasTrio).filter(PassadasTrio.id == passada_id).first()
        if not passada:
            raise ValueError(f"Passada {passada_id} não encontrada")
        
        # Remover SAT usando método do schema
        passada.remover_sat()
        
        # Recalcular colocação se tiver tempo
        if passada.tempo_realizado and passada.status == StatusPassada.EXECUTADA:
            passada.colocacao_passada = self._calcular_colocacao_passada(passada)
        
        self.db.commit()
        self.db.refresh(passada)
        
        # Recalcular colocações das passadas relacionadas
        self._atualizar_colocacoes_relacionadas(passada)
        
        return passada

    def listar_passadas_sat(self, prova_id: Optional[int] = None, categoria_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Lista todas as passadas que receberam SAT"""
        
        query = self.db.query(PassadasTrio).options(
            joinedload(PassadasTrio.trio).joinedload(Trios.integrantes).joinedload(IntegrantesTrios.competidor),
            joinedload(PassadasTrio.trio).joinedload(Trios.categoria),
            joinedload(PassadasTrio.prova)
        ).filter(PassadasTrio.is_sat == True)
        
        if prova_id:
            query = query.filter(PassadasTrio.prova_id == prova_id)
        
        if categoria_id:
            query = query.join(Trios).filter(Trios.categoria_id == categoria_id)
        
        passadas_sat = query.order_by(PassadasTrio.data_sat.desc()).all()
        
        resultado = []
        for passada in passadas_sat:
            competidores_nomes = [i.competidor.nome for i in passada.trio.integrantes if i.competidor]
            
            resultado.append({
                'passada_id': passada.id,
                'trio_id': passada.trio_id,
                'trio_numero': passada.trio.numero_trio,
                'prova_nome': passada.prova.nome,
                'categoria_nome': passada.trio.categoria.nome if passada.trio.categoria else None,
                'numero_passada': passada.numero_passada,
                'competidores_nomes': competidores_nomes,
                'motivo_sat': passada.motivo_sat,
                'desclassificado_por': passada.desclassificado_por,
                'data_sat': passada.data_sat.isoformat() if passada.data_sat else None,
                'tempo_original': float(passada.tempo_realizado) if passada.tempo_realizado else None
            })
        
        return resultado

    def obter_estatisticas_sat(self, prova_id: Optional[int] = None) -> Dict[str, Any]:
        """Obtém estatísticas sobre aplicações de SAT"""
        
        query = self.db.query(PassadasTrio).filter(PassadasTrio.is_sat == True)
        
        if prova_id:
            query = query.filter(PassadasTrio.prova_id == prova_id)
        
        passadas_sat = query.all()
        
        # Estatísticas básicas
        total_sat = len(passadas_sat)
        
        # Agrupar por motivo
        motivos = {}
        for passada in passadas_sat:
            motivo = passada.motivo_sat or "Não informado"
            motivos[motivo] = motivos.get(motivo, 0) + 1
        
        # Agrupar por aplicador
        aplicadores = {}
        for passada in passadas_sat:
            aplicador = passada.desclassificado_por or "Sistema"
            aplicadores[aplicador] = aplicadores.get(aplicador, 0) + 1
        
        # SAT por categoria
        categorias = {}
        for passada in passadas_sat:
            if passada.trio and passada.trio.categoria:
                categoria = passada.trio.categoria.nome
                categorias[categoria] = categorias.get(categoria, 0) + 1
        
        # SAT por data (últimos 30 dias)
        data_limite = datetime.now() - timedelta(days=30)
        sat_recentes = [p for p in passadas_sat if p.data_sat and p.data_sat >= data_limite]
        
        return {
            'total_sat': total_sat,
            'sat_recentes_30_dias': len(sat_recentes),
            'distribuicao_motivos': motivos,
            'distribuicao_aplicadores': aplicadores,
            'distribuicao_categorias': categorias,
            'motivos_mais_comuns': sorted(motivos.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    # ----- Configurações -----
    
    def criar_configuracao(self, config_data: ConfiguracaoPassadasPOST) -> ConfiguracaoPassadasProva:
        """Cria configuração de passadas para prova/categoria"""
        # Verificar se já existe
        config_existente = self.db.query(ConfiguracaoPassadasProva).filter(
            and_(
                ConfiguracaoPassadasProva.prova_id == config_data.prova_id,
                ConfiguracaoPassadasProva.categoria_id == config_data.categoria_id
            )
        ).first()
        
        if config_existente:
            raise ValueError("Configuração já existe para esta prova/categoria")
        
        nova_config = ConfiguracaoPassadasProva(**config_data.dict())
        
        # Converter lista de bois para JSON
        if config_data.bois_disponiveis:
            nova_config.bois_disponiveis = json.dumps(config_data.bois_disponiveis)
        
        self.db.add(nova_config)
        self.db.commit()
        self.db.refresh(nova_config)
        
        return nova_config
    
    def obter_configuracao(self, prova_id: int, categoria_id: int=None) -> Optional[ConfiguracaoPassadasProva]:
        """Obtém configuração de uma prova/categoria"""
        return self._obter_configuracao_prova(prova_id, categoria_id)
    
    def atualizar_configuracao(self, config_id: int, config_data: ConfiguracaoPassadasPUT) -> Optional[ConfiguracaoPassadasProva]:
        """Atualiza configuração"""
        config = self.db.query(ConfiguracaoPassadasProva).filter(
            ConfiguracaoPassadasProva.id == config_id
        ).first()
        
        if not config:
            return None
        
        for campo, valor in config_data.dict(exclude_unset=True).items():
            if campo == 'bois_disponiveis' and valor:
                setattr(config, campo, json.dumps(valor))
            else:
                setattr(config, campo, valor)
        
        self.db.commit()
        self.db.refresh(config)
        
        return config
    
    # ----- Controle de Participação -----
    
    def obter_controle_participacao(self, competidor_id: int, prova_id: int, categoria_id: int) -> Optional[ControleParticipacao]:
        """Obtém controle de participação de um competidor"""
        return self.db.query(ControleParticipacao).filter(
            and_(
                ControleParticipacao.competidor_id == competidor_id,
                ControleParticipacao.prova_id == prova_id,
                ControleParticipacao.categoria_id == categoria_id
            )
        ).first()
    
    def listar_controle_participacao(self, filtros: FiltrosControleParticipacao) -> List[ControleParticipacao]:
        """Lista controles de participação com filtros"""
        query = self.db.query(ControleParticipacao).options(
            joinedload(ControleParticipacao.competidor),
            joinedload(ControleParticipacao.prova),
            joinedload(ControleParticipacao.categoria)
        )
        
        if filtros.competidor_id:
            query = query.filter(ControleParticipacao.competidor_id == filtros.competidor_id)
        
        if filtros.prova_id:
            query = query.filter(ControleParticipacao.prova_id == filtros.prova_id)
        
        if filtros.categoria_id:
            query = query.filter(ControleParticipacao.categoria_id == filtros.categoria_id)
        
        if filtros.apenas_ativos:
            query = query.filter(ControleParticipacao.pode_competir == True)
        
        if filtros.apenas_bloqueados:
            query = query.filter(ControleParticipacao.pode_competir == False)
        
        if filtros.passadas_restantes_min is not None:
            query = query.filter(
                (ControleParticipacao.max_passadas_permitidas - ControleParticipacao.total_passadas_executadas) >= filtros.passadas_restantes_min
            )
        
        return query.order_by(ControleParticipacao.competidor_id).all()
    
    # ----- Validações -----
    
    def validar_passada(self, request: ValidarPassadaRequest) -> ValidacaoPassadaResponse:
        """Valida se uma passada pode ser executada"""
        trio = self.db.query(Trios).filter(Trios.id == request.trio_id).first()
        if not trio:
            return ValidacaoPassadaResponse(
                valida=False,
                trio_pode_competir=False,
                mensagens=["Trio não encontrado"]
            )
        
        # Verificar se trio pode competir
        if trio.status != "ativo":
            return ValidacaoPassadaResponse(
                valida=False,
                trio_pode_competir=False,
                mensagens=["Trio não está ativo"]
            )
        
        # Verificar se número de passada já existe
        passada_existente = self.db.query(PassadasTrio).filter(
            and_(
                PassadasTrio.trio_id == request.trio_id,
                PassadasTrio.numero_passada == request.numero_passada
            )
        ).first()
        
        if passada_existente:
            return ValidacaoPassadaResponse(
                valida=False,
                trio_pode_competir=True,
                mensagens=[f"Passada {request.numero_passada} já existe para este trio"]
            )
        
        # Verificar controle de participação dos competidores
        competidores_bloqueados = []
        for integrante in trio.integrantes:
            controle = self.obter_controle_participacao(
                integrante.competidor_id, trio.prova_id, trio.categoria_id
            )
            
            if controle and not controle.pode_competir:
                competidores_bloqueados.append({
                    'competidor_id': integrante.competidor_id,
                    'nome': integrante.competidor.nome,
                    'motivo': controle.motivo_bloqueio
                })
        
        # Verificar disponibilidade do boi
        boi_disponivel = True
        if request.numero_boi:
            config = self._obter_configuracao_prova(trio.prova_id, trio.categoria_id)
            if config and not config.permite_repetir_boi:
                boi_usado = self.db.query(PassadasTrio).filter(
                    and_(
                        PassadasTrio.prova_id == trio.prova_id,
                        PassadasTrio.numero_boi == request.numero_boi,
                        PassadasTrio.status == StatusPassada.EXECUTADA,
                        # ✅ EXCLUIR SAT da verificação de boi usado
                        or_(
                            PassadasTrio.is_sat.is_(None),
                            PassadasTrio.is_sat == False
                        )
                    )
                ).first()
                
                if boi_usado:
                    boi_disponivel = False
        
        # Verificar intervalo entre passadas
        intervalo_respeitado = True
        ultima_passada = self.db.query(PassadasTrio).filter(
            and_(
                PassadasTrio.trio_id == request.trio_id,
                PassadasTrio.data_hora_passada.isnot(None)
            )
        ).order_by(desc(PassadasTrio.data_hora_passada)).first()
        
        if ultima_passada and ultima_passada.data_hora_passada:
            config = self._obter_configuracao_prova(trio.prova_id, trio.categoria_id)
            if config and config.intervalo_minimo_passadas > 0:
                tempo_passado = datetime.now() - ultima_passada.data_hora_passada
                if tempo_passado.total_seconds() < (config.intervalo_minimo_passadas * 60):
                    intervalo_respeitado = False
        
        # Compilar resultado
        mensagens = []
        restricoes = []
        
        if competidores_bloqueados:
            mensagens.append(f"{len(competidores_bloqueados)} competidor(es) bloqueado(s)")
            restricoes.extend([f"{c['nome']}: {c['motivo']}" for c in competidores_bloqueados])
        
        if not boi_disponivel:
            mensagens.append(f"Boi {request.numero_boi} já foi usado")
            restricoes.append("Repetição de boi não permitida")
        
        if not intervalo_respeitado:
            config = self._obter_configuracao_prova(trio.prova_id, trio.categoria_id)
            mensagens.append(f"Intervalo mínimo de {config.intervalo_minimo_passadas} minutos não respeitado")
            restricoes.append("Aguardar intervalo entre passadas")
        
        valida = len(competidores_bloqueados) == 0 and boi_disponivel and intervalo_respeitado
        
        return ValidacaoPassadaResponse(
            valida=valida,
            trio_pode_competir=trio.status == "ativo",
            competidores_bloqueados=competidores_bloqueados,
            boi_disponivel=boi_disponivel,
            intervalo_respeitado=intervalo_respeitado,
            mensagens=mensagens,
            restricoes=restricoes
        )
    
    # ----- Rankings e Relatórios -----
    
    def obter_ranking_passada(self, prova_id: int, categoria_id: Optional[int] = None, numero_passada: Optional[int] = None, tipo_ranking: str = "tempo") -> List[Dict[str, Any]]:
        """Obtém ranking de uma passada específica (excluindo SAT)"""
        query = self.db.query(PassadasTrio).options(
            joinedload(PassadasTrio.trio).joinedload(Trios.integrantes).joinedload(IntegrantesTrios.competidor)
        ).filter(
            and_(
                PassadasTrio.prova_id == prova_id,
                PassadasTrio.status == StatusPassada.EXECUTADA,
                # ✅ EXCLUIR SAT DO RANKING
                or_(
                    PassadasTrio.is_sat.is_(None),
                    PassadasTrio.is_sat == False
                )
            )
        )
        
        if categoria_id:
            query = query.join(Trios).filter(Trios.categoria_id == categoria_id)
        
        if numero_passada:
            query = query.filter(PassadasTrio.numero_passada == numero_passada)
        
        # Ordenação baseada no tipo
        if tipo_ranking == "tempo":
            query = query.order_by(asc(PassadasTrio.tempo_realizado))
        elif tipo_ranking == "pontos":
            query = query.order_by(desc(PassadasTrio.pontos_passada))
        else:
            query = query.order_by(asc(PassadasTrio.tempo_realizado))
        
        passadas = query.all()
        
        ranking = []
        for posicao, passada in enumerate(passadas, 1):
            competidores_nomes = [i.competidor.nome for i in passada.trio.integrantes if i.competidor]
            
            ranking.append({
                'posicao': posicao,
                'passada_id': passada.id,
                'trio_id': passada.trio_id,
                'trio_numero': passada.trio.numero_trio,
                'numero_passada': passada.numero_passada,
                'tempo_realizado': float(passada.tempo_realizado) if passada.tempo_realizado else None,
                'pontos_passada': float(passada.pontos_passada),
                'numero_boi': passada.numero_boi,
                'competidores_nomes': competidores_nomes,
                'handicap_total': passada.trio.handicap_total
            })
        
        return ranking
    
    def obter_resumo_trio(self, trio_id: int) -> Dict[str, Any]:
        """Obtém resumo de passadas de um trio"""
        passadas = self.db.query(PassadasTrio).filter(PassadasTrio.trio_id == trio_id).all()
        
        if not passadas:
            return {}
        
        trio = passadas[0].trio
        
        total_passadas = len(passadas)
        # ✅ SEPARAR SAT das outras
        passadas_validas = [p for p in passadas if not p.is_sat]
        passadas_sat = [p for p in passadas if p.is_sat]
        
        executadas = [p for p in passadas_validas if p.status == StatusPassada.EXECUTADA]
        no_time = [p for p in passadas_validas if p.status == StatusPassada.NO_TIME]
        pendentes = [p for p in passadas_validas if p.status == StatusPassada.PENDENTE]
        
        tempos_validos = [float(p.tempo_realizado) for p in executadas if p.tempo_realizado]
        
        return {
            'trio_id': trio_id,
            'trio_numero': trio.numero_trio,
            'prova_id': trio.prova_id,
            'categoria_id': trio.categoria_id,
            'total_passadas': total_passadas,
            'passadas_executadas': len(executadas),
            'passadas_no_time': len(no_time),
            'passadas_pendentes': len(pendentes),
            'passadas_sat': len(passadas_sat),  # ✅ NOVO
            'tempo_medio': sum(tempos_validos) / len(tempos_validos) if tempos_validos else None,
            'melhor_tempo': min(tempos_validos) if tempos_validos else None,
            'pior_tempo': max(tempos_validos) if tempos_validos else None,
            'pontos_totais': sum(float(p.pontos_passada) for p in passadas_validas),  # ✅ SÓ VÁLIDAS
            'percentual_conclusao': (len(executadas) / len(passadas_validas) * 100) if passadas_validas else 0,
            'ultima_atualizacao': max(p.updated_at for p in passadas if p.updated_at) if passadas else None
        }
    
    def obter_estatisticas_gerais(self, prova_id: Optional[int] = None, categoria_id: Optional[int] = None) -> Dict[str, Any]:
        """Obtém estatísticas gerais de passadas"""
        query = self.db.query(PassadasTrio)
        
        if prova_id:
            query = query.filter(PassadasTrio.prova_id == prova_id)
        
        if categoria_id:
            query = query.join(Trios).filter(Trios.categoria_id == categoria_id)
        
        passadas = query.all()
        
        if not passadas:
            return {}
        
        # ✅ SEPARAR ESTATÍSTICAS SAT
        passadas_validas = [p for p in passadas if not p.is_sat]
        passadas_sat = [p for p in passadas if p.is_sat]
        
        # Estatísticas básicas
        total_passadas = len(passadas)
        executadas = [p for p in passadas_validas if p.status == StatusPassada.EXECUTADA]
        no_time = [p for p in passadas_validas if p.status == StatusPassada.NO_TIME]
        pendentes = [p for p in passadas_validas if p.status == StatusPassada.PENDENTE]
        
        # Tempos
        tempos_validos = [float(p.tempo_realizado) for p in executadas if p.tempo_realizado]
        
        # Distribuições
        distribuicao_status = {
            StatusPassada.EXECUTADA.value: len(executadas),
            StatusPassada.NO_TIME.value: len(no_time),
            StatusPassada.PENDENTE.value: len(pendentes),
            'sat': len(passadas_sat)  # ✅ NOVO
        }
        
        # Distribuição de bois (excluindo SAT)
        bois_usados = [p.numero_boi for p in passadas_validas if p.numero_boi]
        distribuicao_bois = {}
        for boi in bois_usados:
            distribuicao_bois[boi] = distribuicao_bois.get(boi, 0) + 1
        
        return {
            'total_passadas': total_passadas,
            'passadas_executadas': len(executadas),
            'passadas_no_time': len(no_time),
            'passadas_pendentes': len(pendentes),
            'passadas_sat': len(passadas_sat),  # ✅ NOVO
            'tempo_medio_geral': sum(tempos_validos) / len(tempos_validos) if tempos_validos else None,
            'melhor_tempo_geral': min(tempos_validos) if tempos_validos else None,
            'pior_tempo_geral': max(tempos_validos) if tempos_validos else None,
            'distribuicao_status': distribuicao_status,
            'distribuicao_bois': distribuicao_bois,
            'bois_mais_usados': sorted(distribuicao_bois.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    # ----- Métodos Auxiliares -----
    
    def _obter_configuracao_prova(self, prova_id: int, categoria_id: Optional[int] = None) -> Union[ConfiguracaoPassadasProva, List[ConfiguracaoPassadasProva]]:
        """
        Obtém configuração de passadas para uma prova
        - Se categoria_id informado: retorna configuração específica
        - Se categoria_id None: retorna todas as configurações ativas da prova
        """
        query = self.db.query(ConfiguracaoPassadasProva).filter(
            and_(
                ConfiguracaoPassadasProva.prova_id == prova_id,
                ConfiguracaoPassadasProva.ativa == True
            )
        )
        if categoria_id is not None:
            query = query.filter(ConfiguracaoPassadasProva.categoria_id == categoria_id)
            return query.first()  # Retorna uma configuração específica
        else:
            return query.all()    # Retorna lista de todas as configurações
    
    def _calcular_pontos_tempo(self, tempo_realizado: Decimal, tempo_limite: Decimal) -> Decimal:
        """Calcula pontos baseado no tempo realizado"""
        if tempo_realizado <= tempo_limite:
            # Pontuação inversamente proporcional ao tempo (100 a 50 pontos)
            percentual = float(tempo_realizado) / float(tempo_limite)
            pontos = 100 - (percentual * 50)
            return Decimal(str(round(pontos, 2)))
        else:
            # Penalização por exceder tempo limite
            return Decimal('25.00')
    
    def _gerar_numero_boi_aleatorio(self, bois_disponiveis: List[int], trio_id: int, prova_id: int) -> int:
        """Gera número de boi aleatório disponível"""
        import random
        
        # Obter bois já usados por este trio (excluindo SAT)
        bois_usados_trio = self.db.query(PassadasTrio.numero_boi).filter(
            and_(
                PassadasTrio.trio_id == trio_id,
                PassadasTrio.numero_boi.isnot(None),
                or_(
                    PassadasTrio.is_sat.is_(None),
                    PassadasTrio.is_sat == False
                )
            )
        ).all()
        bois_usados_trio = [b[0] for b in bois_usados_trio]
        
        # Filtrar bois disponíveis
        bois_livres = [b for b in bois_disponiveis if b not in bois_usados_trio]
        
        if bois_livres:
            return random.choice(bois_livres)
        else:
            # Se todos foram usados, permitir repetição
            return random.choice(bois_disponiveis)
    
    def _calcular_colocacao_passada(self, passada: PassadasTrio) -> Optional[int]:
        """Calcula a colocação atual de uma passada baseada no tempo"""
        
        # Só calcular se tiver tempo e status executada
        if not passada.tempo_realizado or passada.status != StatusPassada.EXECUTADA:
            return None
        
        # ✅ VERIFICAR SAT: Não calcular colocação se for SAT
        if passada.is_sat:
            return None
        
        # Buscar todas as passadas executadas da mesma prova, categoria e número
        passadas_comparacao = self.db.query(PassadasTrio).join(Trios).filter(
            and_(
                PassadasTrio.prova_id == passada.prova_id,
                PassadasTrio.numero_passada == passada.numero_passada,
                PassadasTrio.status == StatusPassada.EXECUTADA,
                PassadasTrio.tempo_realizado.isnot(None),
                Trios.categoria_id == passada.trio.categoria_id,
                # ✅ EXCLUIR SAT: Não incluir passadas SAT no ranking
                or_(
                    PassadasTrio.is_sat.is_(None),  # Para compatibilidade
                    PassadasTrio.is_sat == False
                )
            )
        ).all()
        
        # Contar quantas passadas têm tempo melhor (menor)
        tempo_atual = float(passada.tempo_realizado)
        tempos_melhores = 0
        
        for outra_passada in passadas_comparacao:
            if outra_passada.id != passada.id:  # Não comparar consigo mesma
                tempo_comparacao = float(outra_passada.tempo_realizado)
                if tempo_comparacao < tempo_atual:
                    tempos_melhores += 1
        
        # Colocação = quantidade de tempos melhores + 1
        return tempos_melhores + 1

    def _atualizar_colocacoes_relacionadas(self, passada_atualizada: PassadasTrio):
        """Atualiza colocações de passadas relacionadas quando uma passada é alterada"""
        
        # Buscar todas as passadas da mesma prova, categoria e número
        passadas_relacionadas = self.db.query(PassadasTrio).join(Trios).filter(
            and_(
                PassadasTrio.prova_id == passada_atualizada.prova_id,
                PassadasTrio.numero_passada == passada_atualizada.numero_passada,
                PassadasTrio.status == StatusPassada.EXECUTADA,
                PassadasTrio.tempo_realizado.isnot(None),
                Trios.categoria_id == passada_atualizada.trio.categoria_id,
                # ✅ EXCLUIR SAT
                or_(
                    PassadasTrio.is_sat.is_(None),
                    PassadasTrio.is_sat == False
                )
            )
        ).all()
        
        # Ordenar por tempo e atualizar colocações
        passadas_ordenadas = sorted(passadas_relacionadas, key=lambda p: float(p.tempo_realizado))
        
        for posicao, passada in enumerate(passadas_ordenadas, 1):
            if passada.colocacao_passada != posicao:
                passada.colocacao_passada = posicao
                passada.updated_at = datetime.now()
        
        self.db.commit()

    def _obter_status_descricao(self, status: str, is_sat: bool = False) -> str:
        """Retorna descrição amigável do status considerando SAT"""
        if is_sat:
            return "SAT"
        
        status_map = {
            'pendente': "Pendente",
            'executada': "Executada", 
            'no_time': "No Time",
            'desclassificada': "Desclassificada"
        }
        return status_map.get(status, "Status Desconhecido")
    
    def atualizar_resumo_resultado(self, trio_id: int):
        """Atualiza resumo na tabela resultados baseado nas passadas"""
        resumo = self.obter_resumo_trio(trio_id)
        if not resumo:
            return
        
        resultado = self.db.query(Resultados).filter(Resultados.trio_id == trio_id).first()
        
        if not resultado:
            # Criar novo resultado
            resultado = Resultados(trio_id=trio_id, prova_id=resumo['prova_id'])
            self.db.add(resultado)
        
        # Atualizar campos
        resultado.total_passadas = resumo['total_passadas']
        resultado.melhor_tempo = resumo['melhor_tempo']
        resultado.pior_tempo = resumo['pior_tempo'] 
        resultado.tempo_total = resumo['tempo_medio'] * resumo['passadas_executadas'] if resumo['tempo_medio'] else None
        resultado.passadas_no_time = resumo['passadas_no_time']
        resultado.pontos_acumulados = resumo['pontos_totais']
        
        if resumo['tempo_medio']:
            resultado.media_tempo = resumo['tempo_medio']
        
        self.db.commit()

    def obter_ranking_trios(self, prova_id: int, categoria_id: Optional[int] = None, filtros: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Obtém ranking completo de trios com estatísticas detalhadas"""
        from collections import defaultdict
        
        # Buscar todas as passadas da prova (excluindo SAT para ranking)
        query = self.db.query(PassadasTrio).options(
            joinedload(PassadasTrio.trio).joinedload(Trios.integrantes).joinedload(IntegrantesTrios.competidor),
            joinedload(PassadasTrio.trio).joinedload(Trios.categoria)
        ).filter(
            and_(
                PassadasTrio.prova_id == prova_id,
                # ✅ EXCLUIR SAT DO RANKING
                or_(
                    PassadasTrio.is_sat.is_(None),
                    PassadasTrio.is_sat == False
                )
            )
        )
        
        if categoria_id:
            query = query.join(Trios).filter(Trios.categoria_id == categoria_id)
        
        passadas = query.all()
        
        # Agrupar por trio
        stats_trios = defaultdict(lambda: {
            'trio_info': None,
            'passadas': [],
            'total_passadas': 0,
            'passadas_executadas': 0,
            'passadas_no_time': 0,
            'passadas_pendentes': 0,
            'pontos_total': 0,
            'tempos': [],
            'colocacoes': [],
            'melhor_tempo': None,
            'pior_tempo': None,
            'tempo_medio': None,
            'status_geral': 'ativo'
        })
        
        for passada in passadas:
            trio_id = passada.trio_id
            stats = stats_trios[trio_id]
            
            if not stats['trio_info']:
                stats['trio_info'] = passada.trio
            
            stats['passadas'].append(passada)
            stats['total_passadas'] += 1
            stats['pontos_total'] += float(passada.pontos_passada)
            
            if passada.colocacao_passada:
                stats['colocacoes'].append(passada.colocacao_passada)
            
            if passada.status == StatusPassada.EXECUTADA:
                stats['passadas_executadas'] += 1
                if passada.tempo_realizado:
                    tempo = float(passada.tempo_realizado)
                    stats['tempos'].append(tempo)
            elif passada.status == StatusPassada.NO_TIME:
                stats['passadas_no_time'] += 1
            elif passada.status == StatusPassada.PENDENTE:
                stats['passadas_pendentes'] += 1
        
        # Calcular estatísticas finais e criar ranking
        ranking = []
        for trio_id, stats in stats_trios.items():
            if stats['total_passadas'] > 0:
                # Calcular métricas de tempo
                if stats['tempos']:
                    stats['melhor_tempo'] = min(stats['tempos'])
                    stats['pior_tempo'] = max(stats['tempos'])
                    stats['tempo_medio'] = sum(stats['tempos']) / len(stats['tempos'])
                
                # Calcular medalhas
                medalhas = {
                    'ouro': stats['colocacoes'].count(1),
                    'prata': stats['colocacoes'].count(2),
                    'bronze': stats['colocacoes'].count(3)
                }
                
                # Determinar status geral
                if stats['passadas_no_time'] > stats['passadas_executadas']:
                    status_geral = 'eliminado'
                elif stats['passadas_pendentes'] == 0:
                    status_geral = 'finalizado'
                else:
                    status_geral = 'ativo'
                
                ranking.append({
                    'trio_id': trio_id,
                    'trio': {
                        'id': stats['trio_info'].id,
                        'numero_trio': stats['trio_info'].numero_trio,
                        'categoria': {
                            'id': stats['trio_info'].categoria.id,
                            'nome': stats['trio_info'].categoria.nome
                        } if stats['trio_info'].categoria else None,
                        'integrantes': [
                            {
                                'competidor': {
                                    'id': i.competidor.id,
                                    'nome': i.competidor.nome,
                                    'handicap': i.competidor.handicap,
                                    'idade': i.competidor.idade
                                },
                                'funcao': getattr(i, 'funcao', None)
                            }
                            for i in stats['trio_info'].integrantes if i.competidor
                        ] if stats['trio_info'].integrantes else []
                    },
                    'total_passadas': stats['total_passadas'],
                    'passadas_executadas': stats['passadas_executadas'],
                    'passadas_no_time': stats['passadas_no_time'],
                    'passadas_pendentes': stats['passadas_pendentes'],
                    'pontos_total': stats['pontos_total'],
                    'pontos_media': stats['pontos_total'] / stats['total_passadas'],
                    'melhor_tempo': stats['melhor_tempo'],
                    'tempo_medio': stats['tempo_medio'],
                    'taxa_sucesso': (stats['passadas_executadas'] / stats['total_passadas']) * 100,
                    'colocacoes': stats['colocacoes'],
                    'medalhas': medalhas,
                    'status_geral': status_geral,
                    'ultima_passada': max([p.data_hora_passada for p in stats['passadas'] if p.data_hora_passada], default=None)
                })
        
        # Ordenar por pontos total (decrescente) e depois por melhor tempo (crescente)
        ranking.sort(key=lambda x: (-x['pontos_total'], x['melhor_tempo'] or float('inf')))
        
        # Adicionar posições
        for posicao, item in enumerate(ranking, 1):
            item['posicao'] = posicao
        
        return ranking
    
    def obter_ranking_competidores(self, prova_id: int, categoria_id: Optional[int] = None, filtros: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Obtém ranking individual de competidores (excluindo passadas SAT)"""
        from collections import defaultdict
        
        # Buscar todas as passadas da prova (excluindo SAT)
        query = self.db.query(PassadasTrio).options(
            joinedload(PassadasTrio.trio).joinedload(Trios.integrantes).joinedload(IntegrantesTrios.competidor),
            joinedload(PassadasTrio.trio).joinedload(Trios.categoria)
        ).filter(
            and_(
                PassadasTrio.prova_id == prova_id,
                # ✅ EXCLUIR SAT DO RANKING
                or_(
                    PassadasTrio.is_sat.is_(None),
                    PassadasTrio.is_sat == False
                )
            )
        )
        
        if categoria_id:
            query = query.join(Trios).filter(Trios.categoria_id == categoria_id)
        
        passadas = query.all()
        
        # Agrupar por competidor
        stats_competidores = defaultdict(lambda: {
            'competidor_info': None,
            'trio_atual': None,
            'passadas': [],
            'total_passadas': 0,
            'passadas_executadas': 0,
            'pontos_total': 0,
            'tempos': [],
            'categorias_disputadas': set(),
            'participacoes_trios': set()
        })
        
        for passada in passadas:
            if passada.trio and passada.trio.integrantes:
                for integrante in passada.trio.integrantes:
                    if integrante.competidor:
                        comp_id = integrante.competidor.id
                        stats = stats_competidores[comp_id]
                        
                        if not stats['competidor_info']:
                            stats['competidor_info'] = integrante.competidor
                            stats['trio_atual'] = passada.trio
                        
                        stats['passadas'].append(passada)
                        stats['total_passadas'] += 1
                        stats['pontos_total'] += float(passada.pontos_passada)
                        stats['participacoes_trios'].add(passada.trio_id)
                        
                        if passada.trio.categoria:
                            stats['categorias_disputadas'].add(passada.trio.categoria.nome)
                        
                        if passada.status == StatusPassada.EXECUTADA and passada.tempo_realizado:
                            stats['passadas_executadas'] += 1
                            stats['tempos'].append(float(passada.tempo_realizado))
        
        # Gerar ranking
        ranking = []
        for comp_id, stats in stats_competidores.items():
            if stats['total_passadas'] > 0:
                ranking.append({
                    'competidor_id': comp_id,
                    'competidor': {
                        'id': stats['competidor_info'].id,
                        'nome': stats['competidor_info'].nome,
                        'handicap': stats['competidor_info'].handicap,
                        'idade': stats['competidor_info'].idade
                    },
                    'trio_atual': {
                        'id': stats['trio_atual'].id,
                        'numero_trio': stats['trio_atual'].numero_trio
                    } if stats['trio_atual'] else None,
                    'total_passadas': stats['total_passadas'],
                    'passadas_executadas': stats['passadas_executadas'],
                    'pontos_total': stats['pontos_total'],
                    'pontos_media': stats['pontos_total'] / stats['total_passadas'],
                    'melhor_tempo': min(stats['tempos']) if stats['tempos'] else None,
                    'tempo_medio': sum(stats['tempos']) / len(stats['tempos']) if stats['tempos'] else None,
                    'participacoes_trios': len(stats['participacoes_trios']),
                    'categorias_disputadas': list(stats['categorias_disputadas']),
                    'taxa_sucesso': (stats['passadas_executadas'] / stats['total_passadas']) * 100,
                    'ranking_categoria': None  # Será calculado depois se necessário
                })
        
        # Ordenar por pontos total (decrescente)
        ranking.sort(key=lambda x: -x['pontos_total'])
        
        # Adicionar posições
        for posicao, item in enumerate(ranking, 1):
            item['posicao'] = posicao
        
        return ranking
    
    def obter_dashboard_ranking(self, prova_id: int, categoria_id: Optional[int] = None) -> Dict[str, Any]:
        """Obtém dados do dashboard de ranking"""
        
        # Obter rankings
        ranking_trios = self.obter_ranking_trios(prova_id, categoria_id)
        ranking_competidores = self.obter_ranking_competidores(prova_id, categoria_id)
        
        # Calcular resumo geral
        total_trios_ativos = len([t for t in ranking_trios if t['status_geral'] == 'ativo'])
        total_competidores_ativos = len(ranking_competidores)
        
        # Contar passadas finalizadas
        passadas_finalizadas = sum(t['passadas_executadas'] for t in ranking_trios)
        
        # Calcular melhor tempo geral
        todos_tempos = []
        for trio in ranking_trios:
            if trio['melhor_tempo']:
                todos_tempos.append(trio['melhor_tempo'])
        
        melhor_tempo_geral = min(todos_tempos) if todos_tempos else None
        
        # Top performers
        top_performers = {}
        if ranking_trios:
            # Melhor trio (por pontos)
            top_performers['melhor_trio'] = ranking_trios[0]
            
            # Melhor tempo
            trio_melhor_tempo = min(ranking_trios, key=lambda x: x['melhor_tempo'] or float('inf'))
            if trio_melhor_tempo['melhor_tempo']:
                top_performers['melhor_tempo'] = {
                    'tempo': trio_melhor_tempo['melhor_tempo'],
                    'trio': trio_melhor_tempo['trio']
                }
            
            # Maior pontuação
            trio_maior_pontuacao = max(ranking_trios, key=lambda x: x['pontos_total'])
            top_performers['maior_pontuacao'] = {
                'pontos': trio_maior_pontuacao['pontos_total'],
                'trio': trio_maior_pontuacao['trio']
            }
            
            # Mais consistente (maior taxa de sucesso)
            trio_mais_consistente = max(ranking_trios, key=lambda x: x['taxa_sucesso'])
            top_performers['trio_mais_consistente'] = trio_mais_consistente
        
        # Alertas
        alertas = []
        for trio in ranking_trios:
            if trio['status_geral'] == 'ativo' and trio['passadas_pendentes'] == 0:
                alertas.append(f"Trio #{trio['trio']['numero_trio']} sem passadas pendentes")
        
        dashboard = {
            'resumo_geral': {
                'total_trios_ativos': total_trios_ativos,
                'total_competidores_ativos': total_competidores_ativos,
                'passadas_finalizadas': passadas_finalizadas,
                'melhor_tempo_geral': melhor_tempo_geral,
                'media_pontos_geral': sum(t['pontos_total'] for t in ranking_trios) / len(ranking_trios) if ranking_trios else 0
            },
            'top_performers': top_performers,
            'alertas': alertas[:5],  # Máximo 5 alertas
            'ultima_atualizacao': datetime.now().isoformat()
        }
        
        return dashboard
    
    def recalcular_colocacoes_passadas(self, prova_id: int, categoria_id: Optional[int] = None) -> int:
        """Recalcula colocações de todas as passadas de uma prova"""
        
        # Buscar passadas executadas (excluindo SAT)
        query = self.db.query(PassadasTrio).filter(
            and_(
                PassadasTrio.prova_id == prova_id,
                PassadasTrio.status == StatusPassada.EXECUTADA,
                PassadasTrio.tempo_realizado.isnot(None),
                # ✅ EXCLUIR SAT
                or_(
                    PassadasTrio.is_sat.is_(None),
                    PassadasTrio.is_sat == False
                )
            )
        )
        
        if categoria_id:
            query = query.join(Trios).filter(Trios.categoria_id == categoria_id)
        
        passadas = query.all()
        
        # Agrupar por número da passada e categoria
        passadas_por_grupo = {}
        for passada in passadas:
            chave = f"{passada.numero_passada}_{passada.trio.categoria_id}"
            if chave not in passadas_por_grupo:
                passadas_por_grupo[chave] = []
            passadas_por_grupo[chave].append(passada)
        
        colocacoes_atualizadas = 0
        
        # Recalcular colocações para cada grupo
        for chave, grupo_passadas in passadas_por_grupo.items():
            # Ordenar por tempo (crescente)
            grupo_ordenado = sorted(grupo_passadas, key=lambda p: float(p.tempo_realizado))
            
            for posicao, passada in enumerate(grupo_ordenado, 1):
                if passada.colocacao_passada != posicao:
                    passada.colocacao_passada = posicao
                    passada.updated_at = datetime.now()
                    colocacoes_atualizadas += 1
        
        # ✅ ZERAR COLOCAÇÕES DE PASSADAS SAT
        passadas_sat = self.db.query(PassadasTrio).filter(
            and_(
                PassadasTrio.prova_id == prova_id,
                PassadasTrio.is_sat == True
            )
        ).all()
        
        for passada_sat in passadas_sat:
            if passada_sat.colocacao_passada is not None:
                passada_sat.colocacao_passada = None
                passada_sat.updated_at = datetime.now()
                colocacoes_atualizadas += 1
        
        self.db.commit()
        return colocacoes_atualizadas
    
    def obter_analise_tempos(self, prova_id: int, categoria_id: Optional[int] = None) -> Dict[str, Any]:
        """Obtém análise detalhada de distribuição de tempos (excluindo SAT)"""
        
        # Buscar passadas executadas (excluindo SAT)
        filtros = FiltrosPassadas(
            prova_id=prova_id,
            categoria_id=categoria_id,
            status='executada',
            excluir_sat=True,  # ✅ NOVO FILTRO
            tamanho_pagina=10000
        )
        
        passadas, _ = self.listar_passadas(filtros)
        
        if not passadas:
            return {}
        
        tempos = [float(p['tempo_realizado']) for p in passadas if p['tempo_realizado']]
        
        if not tempos:
            return {}
        
        # Estatísticas básicas
        tempo_medio = sum(tempos) / len(tempos)
        tempo_mediano = sorted(tempos)[len(tempos) // 2]
        melhor_tempo = min(tempos)
        pior_tempo = max(tempos)
        
        # Calcular quartis
        tempos_ordenados = sorted(tempos)
        n = len(tempos_ordenados)
        q1 = tempos_ordenados[n // 4]
        q3 = tempos_ordenados[3 * n // 4]
        
        # Distribuição por faixas
        faixas = {
            'ate_45s': len([t for t in tempos if t <= 45]),
            '45_60s': len([t for t in tempos if 45 < t <= 60]),
            '60_75s': len([t for t in tempos if 60 < t <= 75]),
            'acima_75s': len([t for t in tempos if t > 75])
        }
        
        return {
            'total_tempos': len(tempos),
            'tempo_medio': tempo_medio,
            'tempo_mediano': tempo_mediano,
            'melhor_tempo': melhor_tempo,
            'pior_tempo': pior_tempo,
            'quartil_1': q1,
            'quartil_3': q3,
            'amplitude': pior_tempo - melhor_tempo,
            'distribuicao_faixas': faixas,
            'tempos_raw': tempos[:50]  # Primeiros 50 para gráficos
        }
    
    def obter_analise_uso_bois(self, prova_id: int) -> Dict[str, Any]:
        """Obtém análise de uso de bois na prova (excluindo SAT)"""
        
        # Buscar passadas com boi definido (excluindo SAT)
        passadas = self.db.query(PassadasTrio).filter(
            and_(
                PassadasTrio.prova_id == prova_id,
                PassadasTrio.numero_boi.isnot(None),
                # ✅ EXCLUIR SAT
                or_(
                    PassadasTrio.is_sat.is_(None),
                    PassadasTrio.is_sat == False
                )
            )
        ).all()
        
        if not passadas:
            return {}
        
        # Contar uso por boi
        uso_bois = {}
        for passada in passadas:
            boi = passada.numero_boi
            if boi not in uso_bois:
                uso_bois[boi] = {
                    'total_usos': 0,
                    'executadas': 0,
                    'no_time': 0,
                    'pendentes': 0,
                    'tempos': []
                }
            
            uso_bois[boi]['total_usos'] += 1
            
            if passada.status == StatusPassada.EXECUTADA:
                uso_bois[boi]['executadas'] += 1
                if passada.tempo_realizado:
                    uso_bois[boi]['tempos'].append(float(passada.tempo_realizado))
            elif passada.status == StatusPassada.NO_TIME:
                uso_bois[boi]['no_time'] += 1
            elif passada.status == StatusPassada.PENDENTE:
                uso_bois[boi]['pendentes'] += 1
        
        # Calcular estatísticas por boi
        for boi, stats in uso_bois.items():
            if stats['tempos']:
                stats['tempo_medio'] = sum(stats['tempos']) / len(stats['tempos'])
                stats['melhor_tempo'] = min(stats['tempos'])
            else:
                stats['tempo_medio'] = None
                stats['melhor_tempo'] = None
            
            stats['taxa_sucesso'] = (stats['executadas'] / stats['total_usos']) * 100 if stats['total_usos'] > 0 else 0
        
        # Bois mais e menos usados
        bois_mais_usados = sorted(uso_bois.items(), key=lambda x: x[1]['total_usos'], reverse=True)[:10]
        bois_menos_usados = sorted(uso_bois.items(), key=lambda x: x[1]['total_usos'])[:10]
        
        # Bois com melhor performance
        bois_com_tempos = [(boi, stats) for boi, stats in uso_bois.items() if stats['tempo_medio']]
        bois_melhor_tempo = sorted(bois_com_tempos, key=lambda x: x[1]['tempo_medio'])[:10]
        
        return {
            'total_bois_usados': len(uso_bois),
            'total_usos': sum(stats['total_usos'] for stats in uso_bois.values()),
            'uso_por_boi': uso_bois,
            'bois_mais_usados': bois_mais_usados,
            'bois_menos_usados': bois_menos_usados,
            'bois_melhor_tempo': bois_melhor_tempo,
            'media_usos_por_boi': sum(stats['total_usos'] for stats in uso_bois.values()) / len(uso_bois) if uso_bois else 0
        }
    
    def limpar_passadas_antigas(self, dias_limite: int = 30) -> int:
        """Remove passadas pendentes antigas (excluindo SAT)"""
        
        data_limite = datetime.now() - timedelta(days=dias_limite)
        
        passadas_antigas = self.db.query(PassadasTrio).filter(
            and_(
                PassadasTrio.status == StatusPassada.PENDENTE,
                PassadasTrio.created_at < data_limite,
                # ✅ NÃO REMOVER PASSADAS SAT
                or_(
                    PassadasTrio.is_sat.is_(None),
                    PassadasTrio.is_sat == False
                )
            )
        ).all()
        
        quantidade_removida = len(passadas_antigas)
        
        for passada in passadas_antigas:
            self.db.delete(passada)
        
        self.db.commit()
        return quantidade_removida
    
    # ----- Métodos Específicos para Relatórios SAT -----
    
    def gerar_relatorio_sat(self, prova_id: Optional[int] = None, periodo_dias: int = 30) -> Dict[str, Any]:
        """Gera relatório completo de aplicações SAT"""
        
        # Filtrar por período
        data_limite = datetime.now() - timedelta(days=periodo_dias)
        
        query = self.db.query(PassadasTrio).options(
            joinedload(PassadasTrio.trio).joinedload(Trios.integrantes).joinedload(IntegrantesTrios.competidor),
            joinedload(PassadasTrio.trio).joinedload(Trios.categoria),
            joinedload(PassadasTrio.prova)
        ).filter(
            and_(
                PassadasTrio.is_sat == True,
                PassadasTrio.data_sat >= data_limite
            )
        )
        
        if prova_id:
            query = query.filter(PassadasTrio.prova_id == prova_id)
        
        passadas_sat = query.order_by(PassadasTrio.data_sat.desc()).all()
        
        # Estatísticas do período
        total_aplicacoes = len(passadas_sat)
        
        # Análise por motivo
        motivos_stats = {}
        for passada in passadas_sat:
            motivo = passada.motivo_sat or "Não informado"
            if motivo not in motivos_stats:
                motivos_stats[motivo] = {
                    'quantidade': 0,
                    'competidores_afetados': set(),
                    'trios_afetados': set(),
                    'categorias_afetadas': set()
                }
            
            stats = motivos_stats[motivo]
            stats['quantidade'] += 1
            stats['trios_afetados'].add(passada.trio_id)
            
            if passada.trio.categoria:
                stats['categorias_afetadas'].add(passada.trio.categoria.nome)
            
            for integrante in passada.trio.integrantes:
                if integrante.competidor:
                    stats['competidores_afetados'].add(integrante.competidor.nome)
        
        # Converter sets para listas para serialização
        for motivo, stats in motivos_stats.items():
            stats['competidores_afetados'] = list(stats['competidores_afetados'])
            stats['trios_afetados'] = list(stats['trios_afetados'])
            stats['categorias_afetadas'] = list(stats['categorias_afetadas'])
        
        # Análise temporal
        aplicacoes_por_dia = {}
        for passada in passadas_sat:
            if passada.data_sat:
                dia = passada.data_sat.date().isoformat()
                aplicacoes_por_dia[dia] = aplicacoes_por_dia.get(dia, 0) + 1
        
        return {
            'periodo_analisado': {
                'data_inicio': data_limite.isoformat(),
                'data_fim': datetime.now().isoformat(),
                'dias': periodo_dias
            },
            'resumo_geral': {
                'total_aplicacoes': total_aplicacoes,
                'total_competidores_afetados': len(set(
                    comp.nome for passada in passadas_sat 
                    for integrante in passada.trio.integrantes 
                    for comp in [integrante.competidor] if comp
                )),
                'total_trios_afetados': len(set(p.trio_id for p in passadas_sat)),
                'total_categorias_afetadas': len(set(
                    p.trio.categoria.nome for p in passadas_sat 
                    if p.trio.categoria
                ))
            },
            'analise_por_motivo': motivos_stats,
            'aplicacoes_por_dia': aplicacoes_por_dia,
            'detalhes_aplicacoes': [
                {
                    'id': p.id,
                    'trio_numero': p.trio.numero_trio,
                    'prova_nome': p.prova.nome,
                    'categoria': p.trio.categoria.nome if p.trio.categoria else None,
                    'numero_passada': p.numero_passada,
                    'motivo': p.motivo_sat,
                    'aplicado_por': p.desclassificado_por,
                    'data_aplicacao': p.data_sat.isoformat() if p.data_sat else None,
                    'competidores': [
                        i.competidor.nome for i in p.trio.integrantes if i.competidor
                    ]
                }
                for p in passadas_sat
            ]
        }
    
    def obter_historico_sat_competidor(self, competidor_id: int, limite: int = 50) -> List[Dict[str, Any]]:
        """Obtém histórico de SAT para um competidor específico"""
        
        passadas_sat = self.db.query(PassadasTrio).options(
            joinedload(PassadasTrio.trio).joinedload(Trios.categoria),
            joinedload(PassadasTrio.prova)
        ).join(
            Trios
        ).join(
            IntegrantesTrios
        ).filter(
            and_(
                IntegrantesTrios.competidor_id == competidor_id,
                PassadasTrio.is_sat == True
            )
        ).order_by(
            PassadasTrio.data_sat.desc()
        ).limit(limite).all()
        
        historico = []
        for passada in passadas_sat:
            historico.append({
                'passada_id': passada.id,
                'trio_numero': passada.trio.numero_trio,
                'prova_nome': passada.prova.nome,
                'prova_data': passada.prova.data.isoformat() if passada.prova.data else None,
                'categoria': passada.trio.categoria.nome if passada.trio.categoria else None,
                'numero_passada': passada.numero_passada,
                'motivo_sat': passada.motivo_sat,
                'aplicado_por': passada.desclassificado_por,
                'data_sat': passada.data_sat.isoformat() if passada.data_sat else None
            })
        
        return historico
    
    def verificar_tendencias_sat(self, prova_id: int) -> Dict[str, Any]:
        """Verifica tendências e padrões nas aplicações de SAT"""
        
        passadas_sat = self.db.query(PassadasTrio).options(
            joinedload(PassadasTrio.trio).joinedload(Trios.integrantes).joinedload(IntegrantesTrios.competidor),
            joinedload(PassadasTrio.trio).joinedload(Trios.categoria)
        ).filter(
            and_(
                PassadasTrio.prova_id == prova_id,
                PassadasTrio.is_sat == True
            )
        ).all()
        
        if not passadas_sat:
            return {'alertas': [], 'tendencias': {}}
        
        alertas = []
        tendencias = {}
        
        # Competidores com múltiplos SATs
        competidores_sat = {}
        for passada in passadas_sat:
            for integrante in passada.trio.integrantes:
                if integrante.competidor:
                    comp_id = integrante.competidor.id
                    comp_nome = integrante.competidor.nome
                    
                    if comp_id not in competidores_sat:
                        competidores_sat[comp_id] = {
                            'nome': comp_nome,
                            'quantidade': 0,
                            'motivos': []
                        }
                    
                    competidores_sat[comp_id]['quantidade'] += 1
                    competidores_sat[comp_id]['motivos'].append(passada.motivo_sat)
        
        # Competidores com mais de 2 SATs
        competidores_alta_incidencia = [
            comp for comp in competidores_sat.values() if comp['quantidade'] > 2
        ]
        
        if competidores_alta_incidencia:
            alertas.append({
                'tipo': 'competidores_multiplos_sat',
                'descricao': f'{len(competidores_alta_incidencia)} competidor(es) com mais de 2 SATs',
                'detalhes': competidores_alta_incidencia
            })
        
        # Motivos recorrentes
        motivos_count = {}
        for passada in passadas_sat:
            motivo = passada.motivo_sat or "Não informado"
            motivos_count[motivo] = motivos_count.get(motivo, 0) + 1
        
        motivo_predominante = max(motivos_count.items(), key=lambda x: x[1]) if motivos_count else None
        
        if motivo_predominante and motivo_predominante[1] > len(passadas_sat) * 0.3:  # Mais de 30%
            alertas.append({
                'tipo': 'motivo_predominante',
                'descricao': f'Motivo "{motivo_predominante[0]}" representa {motivo_predominante[1]} SATs',
                'percentual': (motivo_predominante[1] / len(passadas_sat)) * 100
            })
        
        tendencias = {
            'total_sat': len(passadas_sat),
            'competidores_afetados': len(competidores_sat),
            'distribuicao_motivos': motivos_count,
            'competidores_multiplos_sat': len(competidores_alta_incidencia)
        }
        
        return {
            'alertas': alertas,
            'tendencias': tendencias,
            'recomendacoes': self._gerar_recomendacoes_sat(alertas, tendencias)
        }
    
    def _gerar_recomendacoes_sat(self, alertas: List[Dict], tendencias: Dict) -> List[str]:
        """Gera recomendações baseadas nos padrões de SAT"""
        recomendacoes = []
        
        if tendencias.get('competidores_multiplos_sat', 0) > 0:
            recomendacoes.append(
                "Considere orientação específica para competidores com múltiplos SATs"
            )
        
        if 'motivo_predominante' in [a['tipo'] for a in alertas]:
            recomendacoes.append(
                "Revisar regulamento ou orientações sobre o motivo de SAT mais comum"
            )
        
        if tendencias.get('total_sat', 0) > tendencias.get('competidores_afetados', 0) * 1.5:
            recomendacoes.append(
                "Alta incidência de SAT pode indicar necessidade de mais orientação geral"
            )
        
        return recomendacoes