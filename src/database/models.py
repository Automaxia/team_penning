from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Generic, TypeVar, List, Union, Dict, Any, Text
from datetime import datetime, date, time
from enum import Enum
import uuid

DataT = TypeVar("DataT")

class ApiResponse(BaseModel, Generic[DataT]):
    """
    Modelo de resposta padronizado para a API, utilizado tanto para sucesso quanto para erro.
    
    Attributes:
        success: Indica se a requisição foi bem-sucedida (True) ou falhou (False)
        data: Dados da resposta, pode ser um único objeto ou uma lista
        message: Mensagem descritiva sobre o resultado da operação
        meta: Informações adicionais como paginação, total de registros, etc.
        status_code: Código de status HTTP da resposta
    """
    success: bool
    data: Optional[Union[DataT, List[DataT], Dict[str, Any]]] = None
    message: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    status_code: int = 200
    
    model_config = ConfigDict(from_attributes=True)

# ----- Enums -----

class StatusTrio(str, Enum):
    ATIVO = "ativo"
    NO_TIME = "no_time"
    DESCLASSIFICADO = "desclassificado"

class TipoCategoria(str, Enum):
    BABY = "baby"
    KIDS = "kids"
    MIRIM = "mirim"
    FEMININA = "feminina"
    ABERTA = "aberta"
    HANDICAP = "handicap"

class TipoCopa(str, Enum):
    REGIONAL = "regional"
    COPA_CAMPEOES = "copa_campeoes"
    TORNEIO_ESPECIAL = "torneio_especial"

# ----- Base Models -----

class BaseTimestampModel(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# ----- Competidores -----

class CompetidorBase(BaseModel):
    nome: str = Field(..., max_length=300, description="Nome completo do competidor")
    data_nascimento: date = Field(..., description="Data de nascimento para cálculo de idade")
    handicap: int = Field(..., ge=0, le=7, description="Handicap do competidor (0-7)")
    cidade: Optional[str] = Field(None, max_length=100, description="Cidade do competidor")
    estado: Optional[str] = Field(None, max_length=2, description="Estado (UF) do competidor")
    sexo: str = Field(..., regex="^[MF]$", description="Sexo do competidor (M/F)")
    ativo: bool = Field(True, description="Status ativo do competidor")
    
    class Config:
        from_attributes = True

class CompetidorPOST(CompetidorBase):
    """Modelo para criação de competidores"""
    pass

class CompetidorPUT(BaseModel):
    """Modelo para atualização de competidores"""
    nome: Optional[str] = Field(None, max_length=300)
    data_nascimento: Optional[date] = None
    handicap: Optional[int] = Field(None, ge=0, le=7)
    cidade: Optional[str] = Field(None, max_length=100)
    estado: Optional[str] = Field(None, max_length=2)
    sexo: Optional[str] = Field(None, regex="^[MF]$")
    ativo: Optional[bool] = None
    
    class Config:
        from_attributes = True

class Competidor(CompetidorBase, BaseTimestampModel):
    """Modelo completo de Competidor"""
    id: int
    idade: Optional[int] = None  # Calculado automaticamente

class CompetidorLista(Competidor):
    """Modelo para listagem de competidores"""
    pass

# ----- Categorias -----

class CategoriaBase(BaseModel):
    nome: str = Field(..., max_length=100, description="Nome da categoria")
    tipo: TipoCategoria = Field(..., description="Tipo da categoria")
    descricao: Optional[str] = Field(None, description="Descrição da categoria")
    handicap_max_trio: Optional[int] = Field(None, description="Handicap máximo para o trio")
    idade_max_trio: Optional[int] = Field(None, description="Idade máxima total para o trio")
    idade_min_individual: Optional[int] = Field(None, description="Idade mínima individual")
    idade_max_individual: Optional[int] = Field(None, description="Idade máxima individual")
    permite_sorteio: bool = Field(False, description="Se permite sorteio")
    min_inscricoes_sorteio: int = Field(3, description="Mínimo de inscrições para sorteio")
    max_inscricoes_sorteio: int = Field(9, description="Máximo de inscrições para sorteio")
    sorteio_completo: bool = Field(False, description="Se é sorteio completo")
    tipo_pontuacao: str = Field("contep", description="Tipo de pontuação")
    ativa: bool = Field(True, description="Status da categoria")
    
    class Config:
        from_attributes = True

class CategoriaPOST(CategoriaBase):
    """Modelo para criação de categorias"""
    pass

class CategoriaPUT(BaseModel):
    """Modelo para atualização de categorias"""
    nome: Optional[str] = Field(None, max_length=100)
    tipo: Optional[TipoCategoria] = None
    descricao: Optional[str] = None
    handicap_max_trio: Optional[int] = None
    idade_max_trio: Optional[int] = None
    idade_min_individual: Optional[int] = None
    idade_max_individual: Optional[int] = None
    permite_sorteio: Optional[bool] = None
    min_inscricoes_sorteio: Optional[int] = None
    max_inscricoes_sorteio: Optional[int] = None
    sorteio_completo: Optional[bool] = None
    tipo_pontuacao: Optional[str] = None
    ativa: Optional[bool] = None
    
    class Config:
        from_attributes = True

class Categoria(CategoriaBase):
    """Modelo completo de Categoria"""
    id: int

class CategoriaLista(Categoria):
    """Modelo para listagem de categorias"""
    pass

# ----- Provas -----

class ProvaBase(BaseModel):
    nome: str = Field(..., max_length=300, description="Nome da prova")
    data: date = Field(..., description="Data da prova")
    rancho: Optional[str] = Field(None, max_length=200, description="Nome do rancho")
    cidade: Optional[str] = Field(None, max_length=100, description="Cidade da prova")
    estado: Optional[str] = Field(None, max_length=2, description="Estado da prova")
    valor_inscricao: Optional[float] = Field(None, description="Valor da inscrição")
    percentual_desconto: float = Field(5.0, description="Percentual de desconto da premiação")
    ativa: bool = Field(True, description="Status da prova")
    tipo_copa: Optional[TipoCopa] = Field(None, description="Tipo de copa/torneio")
    
    class Config:
        from_attributes = True

class ProvaPOST(ProvaBase):
    """Modelo para criação de provas"""
    pass

class ProvaPUT(BaseModel):
    """Modelo para atualização de provas"""
    nome: Optional[str] = Field(None, max_length=300)
    data: Optional[date] = None
    rancho: Optional[str] = Field(None, max_length=200)
    cidade: Optional[str] = Field(None, max_length=100)
    estado: Optional[str] = Field(None, max_length=2)
    valor_inscricao: Optional[float] = None
    percentual_desconto: Optional[float] = None
    ativa: Optional[bool] = None
    tipo_copa: Optional[TipoCopa] = None
    
    class Config:
        from_attributes = True

class Prova(ProvaBase, BaseTimestampModel):
    """Modelo completo de Prova"""
    id: int

class ProvaLista(Prova):
    """Modelo para listagem de provas"""
    pass

# ----- Trios -----

class TrioBase(BaseModel):
    prova_id: int = Field(..., description="ID da prova")
    categoria_id: int = Field(..., description="ID da categoria")
    handicap_total: Optional[int] = Field(None, description="Handicap total do trio")
    idade_total: Optional[int] = Field(None, description="Idade total do trio")
    status: StatusTrio = Field(StatusTrio.ATIVO, description="Status do trio")
    is_cabeca_chave: bool = Field(False, description="Se é cabeça de chave")
    numero_trio: Optional[int] = Field(None, description="Número do trio")
    formacao_manual: bool = Field(False, description="Se foi formado manualmente")
    cup_type: Optional[TipoCopa] = Field(None, description="Tipo de copa")
    
    class Config:
        from_attributes = True

class TrioPOST(TrioBase):
    """Modelo para criação de trios"""
    pass

class TrioPUT(BaseModel):
    """Modelo para atualização de trios"""
    categoria_id: Optional[int] = None
    handicap_total: Optional[int] = None
    idade_total: Optional[int] = None
    status: Optional[StatusTrio] = None
    is_cabeca_chave: Optional[bool] = None
    numero_trio: Optional[int] = None
    formacao_manual: Optional[bool] = None
    cup_type: Optional[TipoCopa] = None
    
    class Config:
        from_attributes = True

class Trio(TrioBase, BaseTimestampModel):
    """Modelo completo de Trio"""
    id: int

class TrioLista(Trio):
    """Modelo para listagem de trios"""
    pass

# ----- Integrantes dos Trios -----

class IntegranteTrioBase(BaseModel):
    trio_id: int = Field(..., description="ID do trio")
    competidor_id: int = Field(..., description="ID do competidor")
    ordem_escolha: Optional[int] = Field(None, description="Ordem de escolha (Copa dos Campeões)")
    is_cabeca_chave: bool = Field(False, description="Se é cabeça de chave")
    
    class Config:
        from_attributes = True

class IntegranteTrioPOST(IntegranteTrioBase):
    """Modelo para criação de integrantes de trio"""
    pass

class IntegranteTrioPUT(BaseModel):
    """Modelo para atualização de integrantes de trio"""
    ordem_escolha: Optional[int] = None
    is_cabeca_chave: Optional[bool] = None
    
    class Config:
        from_attributes = True

class IntegranteTrio(IntegranteTrioBase):
    """Modelo completo de IntegranteTrio"""
    id: int

class IntegranteTrioLista(IntegranteTrio):
    """Modelo para listagem de integrantes de trio"""
    competidor_nome: Optional[str] = None
    competidor_handicap: Optional[int] = None

# ----- Resultados -----

class ResultadoBase(BaseModel):
    trio_id: int = Field(..., description="ID do trio")
    prova_id: int = Field(..., description="ID da prova")
    passada1_tempo: Optional[float] = Field(None, description="Tempo da primeira passada")
    passada2_tempo: Optional[float] = Field(None, description="Tempo da segunda passada")
    media_tempo: Optional[float] = Field(None, description="Média dos tempos")
    colocacao: Optional[int] = Field(None, description="Colocação final")
    premiacao_valor: Optional[float] = Field(None, description="Valor da premiação")
    premiacao_liquida: Optional[float] = Field(None, description="Premiação após desconto")
    no_time: bool = Field(False, description="Se não completou as passadas")
    desclassificado: bool = Field(False, description="Se foi desclassificado")
    observacoes: Optional[str] = Field(None, description="Observações sobre o resultado")
    
    class Config:
        from_attributes = True

class ResultadoPOST(ResultadoBase):
    """Modelo para criação de resultados"""
    pass

class ResultadoPUT(BaseModel):
    """Modelo para atualização de resultados"""
    passada1_tempo: Optional[float] = None
    passada2_tempo: Optional[float] = None
    media_tempo: Optional[float] = None
    colocacao: Optional[int] = None
    premiacao_valor: Optional[float] = None
    premiacao_liquida: Optional[float] = None
    no_time: Optional[bool] = None
    desclassificado: Optional[bool] = None
    observacoes: Optional[str] = None
    
    class Config:
        from_attributes = True

class Resultado(ResultadoBase):
    """Modelo completo de Resultado"""
    id: int

class ResultadoLista(Resultado):
    """Modelo para listagem de resultados"""
    trio_numero: Optional[int] = None
    prova_nome: Optional[str] = None

# ----- Pontuação -----

class PontuacaoBase(BaseModel):
    competidor_id: int = Field(..., description="ID do competidor")
    prova_id: int = Field(..., description="ID da prova")
    categoria_id: int = Field(..., description="ID da categoria")
    pontos_colocacao: float = Field(0, description="Pontos por colocação")
    pontos_premiacao: float = Field(0, description="Pontos por premiação")
    pontos_total: float = Field(0, description="Total de pontos")
    colocacao: Optional[int] = Field(None, description="Colocação obtida")
    premiacao_valor: Optional[float] = Field(None, description="Valor da premiação")
    
    class Config:
        from_attributes = True

class PontuacaoPOST(PontuacaoBase):
    """Modelo para criação de pontuação"""
    pass

class PontuacaoPUT(BaseModel):
    """Modelo para atualização de pontuação"""
    pontos_colocacao: Optional[float] = None
    pontos_premiacao: Optional[float] = None
    pontos_total: Optional[float] = None
    colocacao: Optional[int] = None
    premiacao_valor: Optional[float] = None
    
    class Config:
        from_attributes = True

class Pontuacao(PontuacaoBase, BaseTimestampModel):
    """Modelo completo de Pontuacao"""
    id: int

class PontuacaoLista(Pontuacao):
    """Modelo para listagem de pontuação"""
    competidor_nome: Optional[str] = None
    prova_nome: Optional[str] = None
    categoria_nome: Optional[str] = None

# ----- Modelos Combinados -----

class TrioComIntegrantes(BaseModel):
    """Modelo para criar trio com integrantes em uma operação"""
    trio: TrioPOST
    integrantes: List[int] = Field(..., min_items=3, max_items=3, description="IDs dos 3 competidores")
    
    class Config:
        from_attributes = True

class ResultadoComPontuacao(BaseModel):
    """Modelo para criar resultado e calcular pontuação automaticamente"""
    resultado: ResultadoPOST
    calcular_pontuacao: bool = Field(True, description="Se deve calcular a pontuação automaticamente")
    
    class Config:
        from_attributes = True

class CompetidorRanking(BaseModel):
    """Modelo para exibir ranking de competidores"""
    competidor: Competidor
    total_pontos: float
    total_provas: int
    melhor_colocacao: Optional[int]
    premiacao_total: Optional[float]
    posicao_ranking: int
    
    class Config:
        from_attributes = True

class SorteioRequest(BaseModel):
    """Modelo para requisição de sorteio de trios"""
    prova_id: int = Field(..., description="ID da prova")
    categoria_id: int = Field(..., description="ID da categoria")
    competidores_ids: List[int] = Field(..., min_items=3, description="IDs dos competidores inscritos")
    tipo_sorteio: str = Field("completo", regex="^(completo|parcial)$", description="Tipo de sorteio")
    
    class Config:
        from_attributes = True

class SorteioResponse(BaseModel):
    """Modelo para resposta do sorteio"""
    trios_criados: List[Trio]
    total_trios: int
    competidores_sorteados: int
    competidores_nao_sorteados: List[int]
    mensagem: str
    
    class Config:
        from_attributes = True

# ----- Validadores customizados -----

@validator('handicap')
def validar_handicap(cls, v):
    if v < 0 or v > 7:
        raise ValueError('Handicap deve estar entre 0 e 7')
    return v

@validator('estado')
def validar_estado(cls, v):
    if v and len(v) != 2:
        raise ValueError('Estado deve ter exatamente 2 caracteres')
    return v.upper() if v else v

# Adicionar validadores aos modelos base
CompetidorBase.__validators__['handicap'] = validar_handicap
CompetidorBase.__validators__['estado'] = validar_estado