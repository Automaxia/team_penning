from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, Text, Float, Date, Enum, Numeric
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
    HANDICAP = "handicap"

class TipoCopa(PyEnum):
    REGIONAL = "regional"
    COPA_CAMPEOES = "copa_campeoes"
    TORNEIO_ESPECIAL = "torneio_especial"

class Competidores(Base):
    __tablename__ = 'competidores'
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(300), nullable=False, index=True)
    data_nascimento = Column(Date, nullable=False)
    handicap = Column(Integer, nullable=False, default=0)
    cidade = Column(String(100), nullable=True)
    estado = Column(String(2), nullable=True)
    sexo = Column(String(1), nullable=False)  # M/F para categoria feminina
    ativo = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relacionamentos
    integrantes_trios = relationship('IntegrantesTrios', back_populates='competidor')
    pontuacoes = relationship('Pontuacao', back_populates='competidor')

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
    tipo = Column(Enum(TipoCategoria), nullable=False)
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
    tipo_copa = Column(Enum(TipoCopa), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relacionamentos
    trios = relationship('Trios', back_populates='prova')
    resultados = relationship('Resultados', back_populates='prova')
    pontuacoes = relationship('Pontuacao', back_populates='prova')

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
    status = Column(Enum(StatusTrio), default=StatusTrio.ATIVO)
    is_cabeca_chave = Column(Boolean, default=False)
    numero_trio = Column(Integer, nullable=True)  # Número do trio na prova
    
    # Tipo de formação
    formacao_manual = Column(Boolean, default=False)  # True se formado manualmente
    cup_type = Column(Enum(TipoCopa), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamentos
    prova = relationship('Provas', back_populates='trios')
    categoria = relationship('Categorias', back_populates='trios')
    integrantes = relationship('IntegrantesTrios', back_populates='trio', cascade='all, delete-orphan')
    resultados = relationship('Resultados', back_populates='trio', uselist=False)

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
    premiacao_valor = Column(Numeric(10, 2), nullable=True)  # Valor bruto da premiação
    premiacao_liquida = Column(Numeric(10, 2), nullable=True)  # Após desconto de 5%
    
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