from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, Text, Float, Date, Enum, Numeric, UniqueConstraint, Index
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, date
from enum import Enum as PyEnum
from src.database.db import Base

class StatusTrio(PyEnum):
    ATIVO = "ativo"
    NO_TIME = "no_time"
    DESCLASSIFICADO = "desclassificado"

class TipoCategoria(PyEnum):
    BABY = "baby"
    KIDS = "kids"
    MIRIM = "mirim"
    FEMININA = "feminina"
    ABERTA = "aberta"
    SOMA11 = "soma11"
    SOMA6 = "soma6"
    SOMA1 = "soma1"
    INICIANTE = "iniciante"

class TipoCopa(PyEnum):
    REGIONAL = "regional"
    COPA_CAMPEOES = "copa_campeoes"
    TORNEIO_ESPECIAL = "torneio_especial"
    BOLAO = "bolao"

class StatusPassada(PyEnum):
    PENDENTE = "pendente"
    EXECUTADA = "executada"
    NO_TIME = "no_time"
    DESCLASSIFICADA = "desclassificada"
    SAT = "sat"

class Usuarios(Base):
    __tablename__ = 'usuarios'
    
    sq_usuario = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nu_cpf = Column(String(11), nullable=True, index=True)
    no_nome = Column(String(300), nullable=False)
    no_login = Column(String(50), nullable=False, unique=True, index=True)  # NOVO CAMPO
    no_senha = Column(String(300), nullable=True)
    no_email = Column(String(300), nullable=True, index=True)
    no_foto = Column(Text, nullable=True)
    competidor_id = Column(Integer, ForeignKey('competidores.id', ondelete='SET NULL'), nullable=True)  # NOVO CAMPO
    bo_status = Column(Boolean, server_default='t', default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relacionamento com competidor
    competidor = relationship('Competidores', back_populates='usuario')
    

class Competidores(Base):
    __tablename__ = 'competidores'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(300), nullable=False, index=True)
    data_nascimento = Column(Date, nullable=False)
    handicap = Column(Integer, nullable=False, default=0)
    categoria_id = Column(Integer, ForeignKey('categorias.id'), nullable=True)
    cidade = Column(String(100), nullable=True)
    estado = Column(String(2), nullable=True)
    sexo = Column(String(1), nullable=False)  # M/F para categoria feminina
    ativo = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relacionamentos
    categoria = relationship('Categorias', foreign_keys=[categoria_id])  # ADICIONAR ESTA LINHA
    integrantes_trios = relationship('IntegrantesTrios', back_populates='competidor')
    pontuacoes = relationship('Pontuacao', back_populates='competidor')
    usuario = relationship('Usuarios', back_populates='competidor', uselist=False) 
    controles_participacao = relationship('ControleParticipacao', back_populates='competidor', cascade='all, delete-orphan')

    @hybrid_property
    def idade(self):
        """Calcula idade atual do competidor"""
        if self.data_nascimento:
            hoje = date.today()
            return hoje.year - self.data_nascimento.year - (
                (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day)
            )
        return None

    @validates('handicap')
    def validate_handicap(self, key, value):
        if value < 0 or value > 7:
            raise ValueError("Handicap deve estar entre 0 e 7")
        return value

    @validates('sexo')
    def validate_sexo(self, key, value):
        if value not in ['M', 'F']:
            raise ValueError("Sexo deve ser 'M' ou 'F'")
        return value

    def __repr__(self):
        return f"<Competidor(nome='{self.nome}', handicap={self.handicap}, idade={self.idade})>"

class Categorias(Base):
    __tablename__ = 'categorias'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(100), nullable=False, unique=True)
    tipo = Column(String(30), nullable=False)
    descricao = Column(Text, nullable=True)
    
    # Regras específicas por categoria
    handicap_max_trio = Column(Integer, nullable=True)  # Ex: 11 para handicap
    idade_max_trio = Column(Integer, nullable=True)     # Ex: 36 para mirim
    idade_min_individual = Column(Integer, nullable=True)  # Ex: mínimo para baby
    idade_max_individual = Column(Integer, nullable=True)  # Ex: máximo para kids
    
    # Regras de sorteio
    permite_sorteio = Column(Boolean, default=False)
    min_inscricoes_sorteio = Column(Integer, default=3)
    max_inscricoes_sorteio = Column(Integer, default=9)
    sorteio_completo = Column(Boolean, default=False)  # True para baby
    
    # Sistema de pontuação
    tipo_pontuacao = Column(String(50), default='contep')  # contep, premiacao, misto
    ativa = Column(Boolean, default=True)

    # Relacionamentos
    trios = relationship('Trios', back_populates='categoria')
    pontuacoes = relationship('Pontuacao', back_populates='categoria')
    configuracoes_passadas = relationship('ConfiguracaoPassadasProva', back_populates='categoria', cascade='all, delete-orphan')
    controles_participacao = relationship('ControleParticipacao', back_populates='categoria', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Categoria(nome='{self.nome}', tipo='{self.tipo.value}')>"

class Provas(Base):
    __tablename__ = 'provas'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(300), nullable=False)
    data = Column(Date, nullable=False, index=True)
    rancho = Column(String(200), nullable=True)
    cidade = Column(String(100), nullable=True)
    estado = Column(String(2), nullable=True)
    
    # Financeiro
    valor_inscricao = Column(Numeric(10, 2), nullable=True)
    percentual_desconto = Column(Float, default=5.0)  # 5% desconto padrão
    
    # Status e tipo
    ativa = Column(Boolean, default=True)
    tipo_copa = Column(String(30), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relacionamentos
    trios = relationship('Trios', back_populates='prova')
    resultados = relationship('Resultados', back_populates='prova')
    pontuacoes = relationship('Pontuacao', back_populates='prova')
    passadas = relationship('PassadasTrio', back_populates='prova', cascade='all, delete-orphan')
    configuracoes_passadas = relationship('ConfiguracaoPassadasProva', back_populates='prova', cascade='all, delete-orphan')
    controles_participacao = relationship('ControleParticipacao', back_populates='prova', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Prova(nome='{self.nome}', data='{self.data}')>"

class Trios(Base):
    __tablename__ = 'trios'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prova_id = Column(Integer, ForeignKey('provas.id', ondelete='CASCADE'), nullable=False)
    categoria_id = Column(Integer, ForeignKey('categorias.id', ondelete='CASCADE'), nullable=False)
    
    # Totais calculados
    handicap_total = Column(Integer, nullable=True)
    idade_total = Column(Integer, nullable=True)
    
    # Status e classificação
    status = Column(String(30), default=StatusTrio.ATIVO)
    is_cabeca_chave = Column(Boolean, default=False)
    numero_trio = Column(Integer, nullable=True)  # Número do trio na prova
    
    # Tipo de formação
    formacao_manual = Column(Boolean, default=False)  # True se formado manualmente
    cup_type = Column(String(30), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    prova = relationship('Provas', back_populates='trios')
    categoria = relationship('Categorias', back_populates='trios')
    integrantes = relationship('IntegrantesTrios', back_populates='trio', cascade='all, delete-orphan')
    resultados = relationship('Resultados', back_populates='trio', uselist=False)
    passadas = relationship("PassadasTrio", back_populates="trio", cascade="all, delete-orphan")

    @validates('handicap_total')
    def validate_handicap_total(self, key, value):
        if value and self.categoria and self.categoria.handicap_max_trio:
            if value > self.categoria.handicap_max_trio:
                raise ValueError(f"Handicap total ({value}) excede o máximo permitido ({self.categoria.handicap_max_trio})")
        return value

    @validates('idade_total')
    def validate_idade_total(self, key, value):
        if value and self.categoria and self.categoria.idade_max_trio:
            if value > self.categoria.idade_max_trio:
                raise ValueError(f"Idade total ({value}) excede o máximo permitido ({self.categoria.idade_max_trio})")
        return value

    def calcular_totais(self):
        """Calcula handicap_total e idade_total baseado nos integrantes"""
        if self.integrantes:
            self.handicap_total = sum(i.competidor.handicap for i in self.integrantes if i.competidor)
            self.idade_total = sum(i.competidor.idade for i in self.integrantes if i.competidor and i.competidor.idade)

    def __repr__(self):
        return f"<Trio(id={self.id}, prova='{self.prova.nome if self.prova else 'N/A'}', categoria='{self.categoria.nome if self.categoria else 'N/A'}')>"

class IntegrantesTrios(Base):
    __tablename__ = 'integrantes_trios'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trio_id = Column(Integer, ForeignKey('trios.id', ondelete='CASCADE'), nullable=False)
    competidor_id = Column(Integer, ForeignKey('competidores.id', ondelete='CASCADE'), nullable=False)
    ordem_escolha = Column(Integer, nullable=True)  # Para Copa dos Campeões
    is_cabeca_chave = Column(Boolean, default=False)  # Se este integrante é cabeça de chave

    # Relacionamentos
    trio = relationship('Trios', back_populates='integrantes')
    competidor = relationship('Competidores', back_populates='integrantes_trios')

    def __repr__(self):
        return f"<IntegranteTrio(trio_id={self.trio_id}, competidor='{self.competidor.nome if self.competidor else 'N/A'}')>"

class Resultados(Base):
    __tablename__ = 'resultados'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trio_id = Column(Integer, ForeignKey('trios.id', ondelete='CASCADE'), nullable=False, unique=True)
    prova_id = Column(Integer, ForeignKey('provas.id', ondelete='CASCADE'), nullable=False)
    
    # Tempos das passadas
    passada1_tempo = Column(Float, nullable=True)
    passada2_tempo = Column(Float, nullable=True)
    media_tempo = Column(Float, nullable=True)
    
    # Classificação e premiação
    colocacao = Column(Integer, nullable=True)
    total_passadas = Column(Integer, nullable=True)
    passadas_no_time = Column(Integer, nullable=True)
    pontos_acumulados = Column(Integer, nullable=True)
    premiacao_valor = Column(Numeric(10, 2), nullable=True)  # Valor bruto da premiação
    premiacao_liquida = Column(Numeric(10, 2), nullable=True)  # Após desconto de 5%
    melhor_tempo = Column(Numeric(10, 2), nullable=True)  # Após desconto de 5%
    pior_tempo = Column(Numeric(10, 2), nullable=True)  # Após desconto de 5%
    tempo_total = Column(Numeric(10, 2), nullable=True)  # Após desconto de 5%
    
    # Status
    no_time = Column(Boolean, default=False)  # True se não completou as duas passadas
    desclassificado = Column(Boolean, default=False)
    observacoes = Column(Text, nullable=True)

    # Relacionamentos
    trio = relationship('Trios', back_populates='resultados')
    prova = relationship('Provas', back_populates='resultados')

    def calcular_media(self):
        """Calcula a média se ambas as passadas existem"""
        if self.passada1_tempo is not None and self.passada2_tempo is not None:
            self.media_tempo = (self.passada1_tempo + self.passada2_tempo) / 2
            self.no_time = False
        else:
            self.media_tempo = None
            self.no_time = True

    def calcular_premiacao_liquida(self):
        """Calcula premiação líquida após desconto"""
        if self.premiacao_valor and self.trio and self.trio.prova:
            desconto = self.trio.prova.percentual_desconto or 0
            self.premiacao_liquida = self.premiacao_valor * (1 - desconto / 100)

    def __repr__(self):
        return f"<Resultado(trio_id={self.trio_id}, colocacao={self.colocacao}, media={self.media_tempo})>"

class Pontuacao(Base):
    __tablename__ = 'pontuacao'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    competidor_id = Column(Integer, ForeignKey('competidores.id', ondelete='CASCADE'), nullable=False)
    prova_id = Column(Integer, ForeignKey('provas.id', ondelete='CASCADE'), nullable=False)
    categoria_id = Column(Integer, ForeignKey('categorias.id', ondelete='CASCADE'), nullable=False)
    
    # Pontuação
    pontos_colocacao = Column(Float, nullable=False, default=0)  # Pontos por colocação (tabela CONTEP)
    pontos_premiacao = Column(Float, nullable=True, default=0)   # Pontos por premiação (R$100 = 1pt)
    pontos_total = Column(Float, nullable=False, default=0)      # Total de pontos
    
    # Dados da participação
    colocacao = Column(Integer, nullable=True)
    premiacao_valor = Column(Numeric(10, 2), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    competidor = relationship('Competidores', back_populates='pontuacoes')
    prova = relationship('Provas', back_populates='pontuacoes')
    categoria = relationship('Categorias', back_populates='pontuacoes')

    def calcular_pontos_premiacao(self):
        """Calcula pontos baseado na premiação (R$100 = 1 ponto, R$10 = 0.1 ponto)"""
        if self.premiacao_valor:
            self.pontos_premiacao = float(self.premiacao_valor) / 100
        else:
            self.pontos_premiacao = 0

    def calcular_pontos_colocacao(self):
        """Calcula pontos baseado na colocação (tabela CONTEP)"""
        # Tabela padrão CONTEP (1º ao 10º lugar)
        tabela_pontos = {
            1: 10, 2: 9, 3: 8, 4: 7, 5: 6,
            6: 5, 7: 4, 8: 3, 9: 2, 10: 1
        }
        
        if self.colocacao and self.colocacao in tabela_pontos:
            self.pontos_colocacao = tabela_pontos[self.colocacao]
        else:
            self.pontos_colocacao = 0

    def calcular_pontos_total(self):
        """Calcula pontuação total"""
        self.pontos_total = (self.pontos_colocacao or 0) + (self.pontos_premiacao or 0)

    def __repr__(self):
        return f"<Pontuacao(competidor='{self.competidor.nome if self.competidor else 'N/A'}', pontos={self.pontos_total})>"

class PassadasTrio(Base):
    __tablename__ = 'passadas_trio'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trio_id = Column(Integer, ForeignKey('trios.id', ondelete='CASCADE'), nullable=False)
    prova_id = Column(Integer, ForeignKey('provas.id', ondelete='CASCADE'), nullable=False)
    
    # Controle da passada
    numero_passada = Column(Integer, nullable=False)
    numero_boi = Column(Integer, nullable=True)
    
    # Tempos
    tempo_realizado = Column(Numeric(8, 3), nullable=True)  # Tempo em segundos
    tempo_limite = Column(Numeric(8, 3), default=60.0)     # Tempo limite
    
    # Status da passada
    status = Column(String(20), default=StatusPassada.PENDENTE.value)
    observacoes = Column(Text, nullable=True)
    
    # NOVO: Campos para SAT e desclassificação
    is_sat = Column(Boolean, default=False)  # Indica se foi SAT
    motivo_sat = Column(String(200), nullable=True)  # Motivo do SAT
    desclassificado_por = Column(String(100), nullable=True)  # Quem aplicou a desclassificação
    
    # Pontuação específica desta passada
    pontos_passada = Column(Numeric(8, 2), default=0)
    colocacao_passada = Column(Integer, nullable=True)  # Colocação nesta passada específica
    
    # Timestamps
    data_hora_passada = Column(DateTime(timezone=True), nullable=True)
    data_sat = Column(DateTime(timezone=True), nullable=True)  # NOVO: Quando foi aplicado o SAT
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    trio = relationship('Trios', back_populates='passadas')
    prova = relationship('Provas', back_populates='passadas')
    
    # Constraints e Validações
    __table_args__ = (
        UniqueConstraint('trio_id', 'numero_passada', name='uk_trio_passada'),
        Index('idx_passadas_trio_prova', 'trio_id', 'prova_id'),
        Index('idx_passadas_numero', 'numero_passada'),
        Index('idx_passadas_status', 'status'),
        Index('idx_passadas_tempo', 'tempo_realizado'),
        Index('idx_passadas_data', 'data_hora_passada'),
        Index('idx_passadas_sat', 'is_sat'),  # NOVO: Índice para SAT
    )
    
    @validates('numero_passada')
    def validate_numero_passada(self, key, value):
        if value < 1:
            raise ValueError("Número da passada deve ser maior que zero")
        return value
    
    @validates('numero_boi')
    def validate_numero_boi(self, key, value):
        if value is not None and (value < 1 or value > 50):
            raise ValueError("Número do boi deve estar entre 1 e 50")
        return value
    
    @validates('tempo_realizado')
    def validate_tempo_realizado(self, key, value):
        if value is not None and value < 0:
            raise ValueError("Tempo realizado não pode ser negativo")
        return value
    
    @validates('status')
    def validate_status(self, key, value):
        valid_statuses = [s.value for s in StatusPassada]
        if value not in valid_statuses:
            raise ValueError(f"Status deve ser um dos seguintes: {', '.join(valid_statuses)}")
        return value
    
    # NOVO: Método para aplicar SAT
    def aplicar_sat(self, motivo: str, aplicado_por: str = None):
        """Aplica SAT na passada"""
        self.is_sat = True
        self.status = StatusPassada.SAT.value
        self.motivo_sat = motivo
        self.desclassificado_por = aplicado_por
        self.data_sat = datetime.now()
        self.tempo_realizado = None  # Remove o tempo se existir
        self.pontos_passada = 0  # Zero pontos
    
    # NOVO: Método para remover SAT
    def remover_sat(self):
        """Remove SAT da passada (caso tenha sido aplicado por engano)"""
        self.is_sat = False
        self.motivo_sat = None
        self.desclassificado_por = None
        self.data_sat = None
        self.status = StatusPassada.PENDENTE.value
    
    def calcular_pontos_automatico(self):
        """Calcula pontos automaticamente baseado no tempo"""
        # NOVO: Não calcula pontos se for SAT
        if self.is_sat:
            self.pontos_passada = 0
            return
            
        if self.tempo_realizado and self.tempo_limite:
            if self.tempo_realizado <= self.tempo_limite:
                # Pontuação inversamente proporcional ao tempo (100 a 50 pontos)
                percentual = float(self.tempo_realizado) / float(self.tempo_limite)
                pontos = 100 - (percentual * 50)
                self.pontos_passada = round(pontos, 2)
            else:
                # Penalização por exceder tempo limite
                self.pontos_passada = 25.00
    
    def determinar_status_automatico(self):
        """Determina status automaticamente baseado no tempo"""
        # NOVO: Não muda status se for SAT
        if self.is_sat:
            return
            
        if self.tempo_realizado is None:
            self.status = 'pendente'
        elif self.tempo_realizado > self.tempo_limite:
            self.status = 'no_time'
        else:
            self.status = 'executada'
    
    # NOVO: Propriedade para verificar se é válida para ranking
    @hybrid_property
    def valida_para_ranking(self):
        """Verifica se a passada é válida para cálculos de ranking"""
        return not self.is_sat and self.status != 'sat'
    
    # NOVO: Propriedade para obter descrição do status
    @hybrid_property
    def status_descricao(self):
        """Retorna descrição amigável do status"""
        status_map = {
            StatusPassada.PENDENTE.value: "Pendente",
            StatusPassada.EXECUTADA.value: "Executada",
            StatusPassada.NO_TIME.value: "No Time",
            StatusPassada.DESCLASSIFICADA.value: "Desclassificada",
            StatusPassada.SAT.value: "SAT"
        }
        return status_map.get(self.status, "Status Desconhecido")
    
    def __repr__(self):
        sat_info = " [SAT]" if self.is_sat else ""
        return f"<PassadaTrio(trio_id={self.trio_id}, passada={self.numero_passada}, tempo={self.tempo_realizado}, status={self.status}){sat_info}>"

class ConfiguracaoPassadasProva(Base):
    __tablename__ = 'configuracao_passadas_prova'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prova_id = Column(Integer, ForeignKey('provas.id', ondelete='CASCADE'), nullable=False)
    categoria_id = Column(Integer, ForeignKey('categorias.id', ondelete='CASCADE'), nullable=False)
    
    # Configurações de passadas
    max_passadas_por_trio = Column(Integer, default=1)
    max_corridas_por_pessoa = Column(Integer, default=5)
    
    # Configurações de tempo
    tempo_limite_padrao = Column(Numeric(8, 3), default=60.0)
    intervalo_minimo_passadas = Column(Integer, default=5)  # minutos entre passadas
    
    # Regras de boi
    permite_repetir_boi = Column(Boolean, default=False)
    bois_disponiveis = Column(Text, nullable=True)  # JSON array com números dos bois
    
    # Status
    ativa = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relacionamentos
    prova = relationship('Provas', back_populates='configuracoes_passadas')
    categoria = relationship('Categorias', back_populates='configuracoes_passadas')
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('prova_id', 'categoria_id', name='uk_config_prova_categoria'),
        Index('idx_config_prova', 'prova_id'),
        Index('idx_config_categoria', 'categoria_id'),
        Index('idx_config_ativa', 'ativa'),
    )
    
    def get_bois_disponiveis_list(self):
        """Retorna lista de bois disponíveis a partir do JSON"""
        if self.bois_disponiveis:
            import json
            try:
                return json.loads(self.bois_disponiveis)
            except:
                return []
        return []
    
    def set_bois_disponiveis_list(self, bois_list):
        """Define lista de bois disponíveis como JSON"""
        import json
        self.bois_disponiveis = json.dumps(bois_list)
    
    def __repr__(self):
        return f"<ConfiguracaoPassadas(prova_id={self.prova_id}, categoria_id={self.categoria_id})>"

class ControleParticipacao(Base):
    __tablename__ = 'controle_participacao'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    competidor_id = Column(Integer, ForeignKey('competidores.id', ondelete='CASCADE'), nullable=False)
    prova_id = Column(Integer, ForeignKey('provas.id', ondelete='CASCADE'), nullable=False)
    categoria_id = Column(Integer, ForeignKey('categorias.id', ondelete='CASCADE'), nullable=False)
    
    # Contadores
    total_passadas_executadas = Column(Integer, default=0)
    max_passadas_permitidas = Column(Integer, default=5)
    
    # Controle temporal
    primeira_passada = Column(DateTime(timezone=True), nullable=True)
    ultima_passada = Column(DateTime(timezone=True), nullable=True)
    
    # Status de participação
    pode_competir = Column(Boolean, default=True)
    motivo_bloqueio = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relacionamentos
    competidor = relationship('Competidores', back_populates='controles_participacao')
    prova = relationship('Provas', back_populates='controles_participacao')
    categoria = relationship('Categorias', back_populates='controles_participacao')
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('competidor_id', 'prova_id', 'categoria_id', name='uk_controle_participacao'),
        Index('idx_controle_competidor', 'competidor_id'),
        Index('idx_controle_prova', 'prova_id'),
        Index('idx_controle_categoria', 'categoria_id'),
        Index('idx_controle_status', 'pode_competir'),
    )
    
    @hybrid_property
    def passadas_restantes(self):
        """Calcula passadas restantes"""
        return self.max_passadas_permitidas - self.total_passadas_executadas
    
    @hybrid_property
    def percentual_uso(self):
        """Calcula percentual de uso das passadas"""
        if self.max_passadas_permitidas > 0:
            return (self.total_passadas_executadas / self.max_passadas_permitidas) * 100
        return 0
    
    @validates('total_passadas_executadas')
    def validate_total_passadas(self, key, value):
        if value < 0:
            raise ValueError("Total de passadas executadas não pode ser negativo")
        return value
    
    @validates('max_passadas_permitidas')
    def validate_max_passadas_permitidas(self, key, value):
        if value < 1:
            raise ValueError("Máximo de passadas permitidas deve ser maior que zero")
        return value
    
    def atualizar_contadores(self):
        """Atualiza contadores e verifica bloqueios"""
        if self.total_passadas_executadas >= self.max_passadas_permitidas:
            self.pode_competir = False
            self.motivo_bloqueio = "Limite de passadas atingido"
        
        if self.total_passadas_executadas > 0 and not self.primeira_passada:
            self.primeira_passada = datetime.now()
        
        if self.total_passadas_executadas > 0:
            self.ultima_passada = datetime.now()
    
    def __repr__(self):
        return f"<ControleParticipacao(competidor_id={self.competidor_id}, {self.total_passadas_executadas}/{self.max_passadas_permitidas})>"


# Relacionamentos adicionais para Provas (back_populates)
Provas.trios = relationship('Trios', back_populates='prova')
Provas.resultados = relationship('Resultados', back_populates='prova')
Provas.pontuacoes = relationship('Pontuacao', back_populates='prova')

# Índices para otimização de consultas
from sqlalchemy import Index

# Índices compostos para consultas frequentes
Index('idx_competidor_handicap_idade', Competidores.handicap, Competidores.data_nascimento)
Index('idx_prova_data_ativa', Provas.data, Provas.ativa)
Index('idx_pontuacao_competidor_prova', Pontuacao.competidor_id, Pontuacao.prova_id)
Index('idx_trio_prova_categoria', Trios.prova_id, Trios.categoria_id)
Index('idx_resultado_colocacao', Resultados.colocacao)