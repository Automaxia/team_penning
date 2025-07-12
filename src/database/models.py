from pydantic import BaseModel, EmailStr, Field, ConfigDict, validator
from typing import Optional, Generic, TypeVar, List, Union, Dict, Any, Text
from datetime import datetime, date, time
from enum import Enum
from decimal import Decimal
from pydantic import field_validator
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
    SOMA11 = "soma11"
    SOMA6 = "soma6"
    SOMA1 = "soma1"

class TipoCopa(str, Enum):
    PROVA_REGULAR = "prova_regular"
    REGIONAL = "regional"
    COPA_CAMPEOES = "copa_campeoes"
    TORNEIO_ESPECIAL = "torneio_especial"
    BOLAO = "bolao"

class StatusPassada(str, Enum):
    PENDENTE = "pendente"
    EXECUTADA = "executada"
    NO_TIME = "no_time"
    DESCLASSIFICADA = "desclassificada"
    SAT = "sat"

class TipoRanking(str, Enum):
    TEMPO = "tempo"
    PONTOS = "pontos"
    GERAL = "geral"
    TRIO = "trio"
    COMPETIDOR = "competidor"

class AplicarSatRequest(BaseModel):
    motivo: str
    aplicado_por: str

# ----- Base Models -----
class BaseTimestampModel(BaseModel):
    """Modelo base com campos de timestamp"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class BaseStatusModel(BaseTimestampModel):
    """Modelo base com campos de timestamp e status"""
    bo_status: bool = True
    
    model_config = ConfigDict(from_attributes=True)

class CompetidorBase(BaseModel):
    nome: str = Field(..., max_length=300, description="Nome completo do competidor")
    data_nascimento: date = Field(..., description="Data de nascimento para cálculo de idade")
    handicap: int = Field(..., ge=0, le=7, description="Handicap do competidor (0-7)")
    cidade: Optional[str] = Field(None, max_length=100, description="Cidade do competidor")
    estado: Optional[str] = Field(None, max_length=2, description="Estado (UF) do competidor")
    sexo: str = Field(..., pattern="^[MF]$", description="Sexo do competidor (M/F)")
    ativo: bool = Field(True, description="Status ativo do competidor")
    categoria_id: Optional[int] = Field(None, description="ID da categoria principal")

    @field_validator('handicap')
    @classmethod
    def validar_handicap(cls, v):
        if v < 0 or v > 7:
            raise ValueError('Handicap deve estar entre 0 e 7')
        return v

    @field_validator('estado')
    @classmethod
    def validar_estado(cls, v):
        if v and len(v) != 2:
            raise ValueError('Estado deve ter exatamente 2 caracteres')
        return v.upper() if v else v

    class Config:
        from_attributes = True

class CompetidorPUT(BaseModel):
    """Modelo para atualização de competidores"""
    nome: Optional[str] = Field(None, max_length=300)
    data_nascimento: Optional[date] = None
    handicap: Optional[int] = Field(None, ge=0, le=7)
    cidade: Optional[str] = Field(None, max_length=100)
    estado: Optional[str] = Field(None, max_length=2)
    sexo: Optional[str] = Field(None, pattern="^[MF]$")
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

class SenhaAcessoUsuario(BaseModel):
    nu_cpf: str
    no_senha: str
    no_senha_confirma: str

class LoginRequest(BaseModel):
    """Modelo para requisição de login"""
    username: str = Field(..., min_length=3, max_length=50, description="Login do usuário")
    password: str = Field(..., min_length=6, description="Senha do usuário")
    
    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    """Modelo para resposta de login"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: 'UsuarioCompleto'
    
    class Config:
        from_attributes = True

class CadastroCompletoRequest(BaseModel):
    """Modelo para cadastro completo de competidor + usuário"""
    # Dados do competidor
    nome: str = Field(..., max_length=300, description="Nome completo do competidor")
    data_nascimento: date = Field(..., description="Data de nascimento")
    handicap: int = Field(..., ge=0, le=7, description="Handicap (0-7)")
    cidade: Optional[str] = Field(None, max_length=100, description="Cidade")
    estado: Optional[str] = Field(None, max_length=2, description="Estado (UF)")
    sexo: str = Field(..., pattern="^[MF]$", description="Sexo (M/F)")
    
    # Dados de acesso
    login: str = Field(..., min_length=3, max_length=50, description="Login único")
    senha: str = Field(..., min_length=6, description="Senha de acesso")
    
    @field_validator('estado')
    @classmethod
    def validar_estado(cls, v):
        if v and len(v) != 2:
            raise ValueError('Estado deve ter exatamente 2 caracteres')
        return v.upper() if v else v
    
    @field_validator('login')
    @classmethod
    def validar_login(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Login deve conter apenas letras, números, pontos, hífens e underscores')
        return v.lower()
    
    class Config:
        from_attributes = True

class CadastroCompletoResponse(BaseModel):
    """Resposta do cadastro completo"""
    competidor: Competidor
    usuario: 'UsuarioCompleto'
    mensagem: str
    
    class Config:
        from_attributes = True

class AlterarSenhaRequest(BaseModel):
    """Modelo para alteração de senha"""
    senha_atual: str = Field(..., description="Senha atual")
    nova_senha: str = Field(..., min_length=6, description="Nova senha")
    confirmar_senha: str = Field(..., description="Confirmação da nova senha")
    
    @field_validator('confirmar_senha')
    @classmethod
    def senhas_devem_coincidir(cls, v, info):
        if 'nova_senha' in info.data and v != info.data['nova_senha']:
            raise ValueError('Senhas não coincidem')
        return v
    
    class Config:
        from_attributes = True

class RecuperarSenhaRequest(BaseModel):
    """Modelo para solicitação de recuperação de senha"""
    email: EmailStr = Field(..., description="Email para recuperação")
    
    class Config:
        from_attributes = True

class RedefinirSenhaRequest(BaseModel):
    """Modelo para redefinição de senha com token"""
    token: str = Field(..., description="Token de recuperação")
    nova_senha: str = Field(..., min_length=6, description="Nova senha")
    confirmar_senha: str = Field(..., description="Confirmação da nova senha")
    
    @field_validator('confirmar_senha')
    @classmethod
    def senhas_devem_coincidir(cls, v, info):
        if 'nova_senha' in info.data and v != info.data['nova_senha']:
            raise ValueError('Senhas não coincidem')
        return v
    
    class Config:
        from_attributes = True

class UsuarioBase(BaseModel):
    """Atributos base do modelo Usuário"""
    nu_cpf: Optional[str] = None
    no_nome: str
    no_email: Optional[EmailStr] = None
    no_senha: Optional[str] = None
    no_foto: Optional[str] = None
    no_login: Optional[str] = None
    competidor_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class UsuarioPOST(UsuarioBase):
    """Modelo para criação de usuários"""

class UsuarioPUT(BaseModel):
    """Modelo para atualização de usuários"""
    no_nome: Optional[str] = None
    no_email: Optional[EmailStr] = None
    no_foto: Optional[str] = None
    bo_status: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)

class Usuario(UsuarioBase, BaseStatusModel):
    """Modelo completo de Usuário"""
    sq_usuario: int

class UsuarioLista(Usuario):
    """Modelo para listagem de usuários"""
    no_senha: Optional[str] = None

class LoginSucesso(BaseModel):
    """Retorno de login bem-sucedido"""
    success: bool = True
    usuario: UsuarioLista
    access_token: str
    token_type: str = 'bearer'
    message: str = 'Login realizado com sucesso!'
    
    model_config = ConfigDict(from_attributes=True)

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
    sexo: Optional[str] = Field(None, pattern="^[MF]$")
    ativo: Optional[bool] = None
    categoria_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class CompetidorCategoria(BaseModel):
    """Modelo para relacionamento competidor-categoria"""
    id: int
    competidor_id: int
    categoria_id: int
    elegivel: bool = True
    preferencial: bool = False
    observacoes: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class CompetidorCategoriaRequest(BaseModel):
    """Modelo para criar/atualizar relacionamento competidor-categoria"""
    categoria_id: int = Field(..., description="ID da categoria")
    elegivel: bool = Field(True, description="Se o competidor é elegível")
    preferencial: bool = Field(False, description="Se é a categoria preferencial")
    observacoes: Optional[str] = Field(None, description="Observações específicas")
    
    class Config:
        from_attributes = True

class Competidor(CompetidorBase, BaseTimestampModel):
    """Modelo completo de Competidor"""
    id: int
    idade: Optional[int] = None  # Calculado automaticamente

    categoria_principal: Optional['CategoriaResumo'] = None
    categorias_elegiveis: List[CompetidorCategoria] = []
    categorias_disponiveis: List[str] = []  # Calculado baseado em idade/sexo
    categoria_sugerida: Optional[str] = None  # Calculado

class CompetidorLista(Competidor):
    """Modelo para listagem de competidores"""
    pass


class CompetidorResumo(BaseModel):
    """Modelo resumido para uso em outras entidades"""
    id: int
    nome: str
    handicap: int
    idade: Optional[int] = None
    sexo: str
    categoria_nome: Optional[str] = None
    
    class Config:
        from_attributes = True

class CompetidorComCategoria(BaseModel):
    """Modelo de competidor com informações da categoria"""
    id: int
    nome: str
    data_nascimento: date
    handicap: int
    categoria_id: Optional[int] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    sexo: str
    ativo: bool
    idade: Optional[int] = None
    
    # Informações da categoria
    categoria_nome: Optional[str] = None
    categoria_tipo: Optional[str] = None
    categoria_descricao: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class SugestaoCategoria(BaseModel):
    """Modelo para sugestão de categoria"""
    categoria_id: int
    categoria_nome: str
    categoria_tipo: str
    motivo: str
    prioridade: int
    elegivel: bool = True
    
    class Config:
        from_attributes = True

class EstatisticasCategoria(BaseModel):
    """Estatísticas de uma categoria"""
    categoria_id: Optional[int] = None
    categoria_nome: Optional[str] = None
    categoria_tipo: Optional[str] = None
    total_competidores: int = 0
    competidores_ativos: int = 0
    media_handicap: Optional[float] = None
    total_feminino: int = 0
    total_masculino: int = 0
    
    class Config:
        from_attributes = True

class FiltrosCompetidorAvancados(BaseModel):
    """Filtros avançados para busca de competidores"""
    nome: Optional[str] = None
    handicap: Optional[int] = Field(None, ge=0, le=7)
    cidade: Optional[str] = None
    estado: Optional[str] = None
    sexo: Optional[str] = Field(None, pattern="^[MF]$")
    idade_min: Optional[int] = Field(None, ge=0, le=100)
    idade_max: Optional[int] = Field(None, ge=0, le=100)
    categoria_id: Optional[int] = None
    categoria_tipo: Optional[str] = None
    apenas_com_categoria: Optional[bool] = None
    ativo: Optional[bool] = True
    pagina: Optional[int] = Field(0, ge=0)
    tamanho_pagina: Optional[int] = Field(0, ge=0)
    
    class Config:
        from_attributes = True

class CategoriaResumo(BaseModel):
    """Modelo resumido de categoria"""
    id: int
    nome: str
    tipo: str
    
    class Config:
        from_attributes = True

class CompetidorCategoriasBatch(BaseModel):
    """Modelo para operações em lote de categorias"""
    competidor_id: int = Field(..., description="ID do competidor")
    categorias: List[CompetidorCategoriaRequest] = Field(..., description="Lista de categorias")
    
    class Config:
        from_attributes = True

class CompetidorCategoriasResponse(BaseModel):
    """Resposta com informações completas de categorias do competidor"""
    competidor: CompetidorResumo
    categoria_principal: Optional[CategoriaResumo] = None
    categorias_elegiveis: List[Dict[str, Any]] = []  # Categoria + status de elegibilidade
    categorias_disponiveis: List[str] = []  # Baseado em regras automáticas
    categoria_sugerida: Optional[str] = None
    total_categorias: int = 0
    
    class Config:
        from_attributes = True

class SugestaoCategoria(BaseModel):
    """Modelo para sugestão de categoria"""
    categoria_tipo: str = Field(..., description="Tipo da categoria sugerida")
    categoria_nome: str = Field(..., description="Nome da categoria")
    categoria_id: Optional[int] = Field(None, description="ID da categoria (se existir)")
    motivo: str = Field(..., description="Motivo da sugestão")
    elegivel: bool = Field(..., description="Se o competidor é elegível")
    
    class Config:
        from_attributes = True

class CompetidorElegibilidade(BaseModel):
    """Modelo para verificar elegibilidade em categoria"""
    competidor_id: int = Field(..., description="ID do competidor")
    categoria_id: int = Field(..., description="ID da categoria")
    elegivel: bool = Field(..., description="Se é elegível")
    motivos: List[str] = Field(..., description="Motivos da elegibilidade/inelegibilidade")
    restricoes: List[str] = Field(default=[], description="Restrições encontradas")
    
    class Config:
        from_attributes = True

# ----- Categorias -----

class CategoriaBase(BaseModel):
    nome: str = Field(..., max_length=100, description="Nome da categoria")
    tipo: str = Field(..., description="Tipo da categoria")
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
    tipo: Optional[str] = None
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

class CompetidorFiltros(BaseModel):
    """Filtros avançados para busca de competidores"""
    nome: Optional[str] = None
    handicap: Optional[int] = Field(None, ge=0, le=7)
    cidade: Optional[str] = None
    estado: Optional[str] = None
    sexo: Optional[str] = Field(None, pattern="^[MF]$")
    idade_min: Optional[int] = Field(None, ge=0, le=100)
    idade_max: Optional[int] = Field(None, ge=0, le=100)
    ativo: Optional[bool] = True
    
    # NOVOS: Filtros por categoria
    categoria_id: Optional[int] = None
    categoria_tipo: Optional[str] = None
    apenas_com_categoria: Optional[bool] = None  # True = apenas com categoria definida
    
    class Config:
        from_attributes = True

class EstatisticasCompetidorCategoria(BaseModel):
    """Estatísticas de competidores por categoria"""
    categoria_id: int
    categoria_nome: str
    categoria_tipo: str
    total_competidores: int = 0
    competidores_ativos: int = 0
    competidores_preferenciais: int = 0  # Que têm esta como principal
    media_handicap: Optional[float] = None
    media_idade: Optional[float] = None
    distribuicao_sexo: Dict[str, int] = {}
    
    class Config:
        from_attributes = True

class EstatisticasGeraisComCategorias(BaseModel):
    """Estatísticas gerais incluindo informações de categoria"""
    total_competidores: int
    distribuicao_sexo: Dict[str, int]
    distribuicao_handicap: Dict[str, int]
    distribuicao_faixa_etaria: Dict[str, int]
    
    # NOVO: Estatísticas de categoria
    distribuicao_categorias: Dict[str, int]
    competidores_sem_categoria: int
    competidores_multiplas_categorias: int
    por_categoria: List[EstatisticasCompetidorCategoria]
    
    class Config:
        from_attributes = True

# ----- Validação de Trio Atualizada -----

class ValidacaoTrioComCategoria(BaseModel):
    """Validação de trio considerando categorias"""
    competidores_ids: List[int] = Field(..., min_items=3, max_items=3)
    categoria_id: int = Field(..., description="ID da categoria")
    verificar_elegibilidade: bool = Field(True, description="Verificar elegibilidade individual")
    
    class Config:
        from_attributes = True

class ResultadoValidacaoTrio(BaseModel):
    """Resultado da validação de trio"""
    valido: bool
    competidores: List[CompetidorResumo]
    categoria: CategoriaResumo
    total_handicap: int
    total_idade: int
    restricoes_violadas: List[str] = []
    avisos: List[str] = []
    elegibilidade_individual: List[Dict[str, Any]] = []
    
    class Config:
        from_attributes = True

# ----- Operações de Categoria -----

class CompetidorMigrarCategoria(BaseModel):
    """Modelo para migrar competidores entre categorias"""
    competidores_ids: List[int] = Field(..., description="IDs dos competidores")
    categoria_origem_id: Optional[int] = Field(None, description="Categoria de origem (opcional)")
    categoria_destino_id: int = Field(..., description="Categoria de destino")
    manter_elegibilidade_origem: bool = Field(True, description="Manter elegibilidade na categoria origem")
    definir_como_principal: bool = Field(False, description="Definir como categoria principal")
    
    class Config:
        from_attributes = True

class ResultadoMigracao(BaseModel):
    """Resultado da migração de categorias"""
    total_processados: int
    migracoes_sucesso: int
    migracoes_erro: int
    competidores_processados: List[Dict[str, Any]]
    erros: List[Dict[str, Any]] = []
    
    class Config:
        from_attributes = True   
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
    tipo_copa: Optional[str] = Field(None, description="Tipo de copa/torneio")
    
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
    tipo_copa: Optional[str] = None
    
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
    status: str = Field('ativo', description="Status do trio")
    is_cabeca_chave: bool = Field(False, description="Se é cabeça de chave")
    numero_trio: Optional[int] = Field(None, description="Número do trio")
    formacao_manual: bool = Field(False, description="Se foi formado manualmente")
    cup_type: Optional[str] = Field(None, description="Tipo de copa")
    
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
    status: Optional[str] = None
    is_cabeca_chave: Optional[bool] = None
    numero_trio: Optional[int] = None
    formacao_manual: Optional[bool] = None
    cup_type: Optional[str] = None
    
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
    tipo_sorteio: str = Field("completo", pattern="^(completo|parcial)$", description="Tipo de sorteio")
    
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

class PassadaTrioBase(BaseModel):
    trio_id: int = Field(..., description="ID do trio")
    prova_id: int = Field(..., description="ID da prova")
    numero_passada: int = Field(..., ge=1, description="Número da passada")
    numero_boi: Optional[int] = Field(None, ge=1, le=50, description="Número do boi selecionado")
    tempo_realizado: Optional[Decimal] = Field(None, ge=0, decimal_places=3, description="Tempo em segundos")
    tempo_limite: Decimal = Field(60.0, ge=10, decimal_places=3, description="Tempo limite")
    status: str = Field('pendente', description="Status da passada")
    observacoes: Optional[str] = Field(None, description="Observações da passada")
    pontos_passada: Decimal = Field(0, ge=0, decimal_places=2, description="Pontos desta passada")
    colocacao_passada: Optional[int] = Field(None, ge=1, description="Colocação nesta passada")
    data_hora_passada: Optional[datetime] = Field(None, description="Data/hora da execução")
    
    @validator('tempo_realizado')
    def validar_tempo(cls, v, values):
        if v is not None:
            tempo_limite = values.get('tempo_limite', 60.0)
            if v > tempo_limite * 2:  # Permitir até 2x o tempo limite
                raise ValueError(f'Tempo muito alto: {v}s (limite: {tempo_limite}s)')
        return v
    
    @validator('numero_boi')
    def validar_boi(cls, v):
        if v is not None and (v < 1 or v > 50):
            raise ValueError('Número do boi deve estar entre 1 e 50')
        return v
    
    class Config:
        from_attributes = True

class PassadaTrioPOST(PassadaTrioBase):
    """Modelo para criação de passadas"""
    pass

class PassadaTrioPUT(BaseModel):
    """Modelo para atualização de passadas"""
    numero_boi: Optional[int] = Field(None, ge=1, le=50)
    tempo_realizado: Optional[Decimal] = Field(None, ge=0, decimal_places=3)
    tempo_limite: Optional[Decimal] = Field(None, ge=10, decimal_places=3)
    status: Optional[str] = None
    observacoes: Optional[str] = None
    pontos_passada: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    colocacao_passada: Optional[int] = Field(None, ge=1)
    data_hora_passada: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class PassadaTrio(PassadaTrioBase):
    """Modelo completo de PassadaTrio"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class PassadaTrioLista(PassadaTrio):
    """Modelo para listagem de passadas"""
    trio_numero: Optional[int] = None
    prova_nome: Optional[str] = None
    competidores_nomes: Optional[List[str]] = []

# ----- Configuração de Passadas -----

class ConfiguracaoPassadasBase(BaseModel):
    prova_id: int = Field(..., description="ID da prova")
    categoria_id: int = Field(..., description="ID da categoria")
    max_passadas_por_trio: int = Field(1, description="Máximo de passadas por trio")
    max_corridas_por_pessoa: int = Field(5, description="Máximo de corridas por pessoa")
    tempo_limite_padrao: Decimal = Field(60.0, decimal_places=3, description="Tempo limite padrão")
    intervalo_minimo_passadas: int = Field(5, description="Intervalo mínimo entre passadas (min)")
    permite_repetir_boi: bool = Field(False, description="Permite repetir número do boi")
    bois_disponiveis: Optional[List[int]] = Field(None, description="Lista de bois disponíveis")
    ativa: bool = Field(True, description="Configuração ativa")
    
    @validator('bois_disponiveis')
    def validar_bois(cls, v):
        if v is not None:
            for boi in v:
                if boi < 1 or boi > 50:
                    raise ValueError(f'Número de boi inválido: {boi}')
        return v
    
    class Config:
        from_attributes = True

class ConfiguracaoPassadasPOST(ConfiguracaoPassadasBase):
    """Modelo para criação de configuração"""
    pass

class ConfiguracaoPassadasPUT(BaseModel):
    """Modelo para atualização de configuração"""
    max_passadas_por_trio: Optional[int] = None
    max_corridas_por_pessoa: Optional[int] = None
    tempo_limite_padrao: Optional[Decimal] = Field(None, decimal_places=3)
    intervalo_minimo_passadas: Optional[int] = None
    permite_repetir_boi: Optional[bool] = None
    bois_disponiveis: Optional[List[int]] = None
    ativa: Optional[bool] = None
    
    class Config:
        from_attributes = True

class ConfiguracaoPassadas(ConfiguracaoPassadasBase):
    """Modelo completo de ConfiguracaoPassadas"""
    id: int
    created_at: Optional[datetime] = None

# ----- Controle de Participação -----

class ControleParticipacaoBase(BaseModel):
    competidor_id: int = Field(..., description="ID do competidor")
    prova_id: int = Field(..., description="ID da prova")
    categoria_id: int = Field(..., description="ID da categoria")
    total_passadas_executadas: int = Field(0, ge=0, description="Total de passadas executadas")
    max_passadas_permitidas: int = Field(5, ge=1, description="Máximo de passadas permitidas")
    pode_competir: bool = Field(True, description="Se pode competir")
    motivo_bloqueio: Optional[str] = Field(None, description="Motivo do bloqueio")
    primeira_passada: Optional[datetime] = Field(None, description="Data da primeira passada")
    ultima_passada: Optional[datetime] = Field(None, description="Data da última passada")
    
    class Config:
        from_attributes = True

class ControleParticipacao(ControleParticipacaoBase):
    """Modelo completo de ControleParticipacao"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Campos calculados
    passadas_restantes: Optional[int] = None
    percentual_uso: Optional[float] = None

# ----- Modelos de Relatórios e Resumos -----

class ResumoPassadasTrio(BaseModel):
    """Resumo de passadas de um trio"""
    trio_id: int
    trio_numero: Optional[int] = None
    prova_id: int
    categoria_id: int
    total_passadas: int = 0
    passadas_executadas: int = 0
    passadas_no_time: int = 0
    passadas_pendentes: int = 0
    is_sat: bool = False
    motivo_sat: Optional[str] = None
    pontos_passadas: Decimal = 0
    colocacao_passadas: Optional[int] = None
    desclassificado_por: Optional[str] = None
    tempo_medio: Optional[float] = None
    melhor_tempo: Optional[float] = None
    pior_tempo: Optional[float] = None
    pontos_totais: Decimal = 0
    ultima_atualizacao: Optional[datetime] = None
    
    # Campos calculados
    percentual_conclusao: Optional[float] = None
    status_geral: Optional[str] = None
    
    class Config:
        from_attributes = True

class RankingPassada(BaseModel):
    """Ranking de uma passada específica"""
    trio_id: int
    trio_numero: Optional[int] = None
    numero_passada: int
    tempo_realizado: Optional[float] = None
    pontos_passada: Decimal = 0
    colocacao_passada: Optional[int] = None
    ranking_tempo: Optional[int] = None
    ranking_pontos: Optional[int] = None
    
    # Dados do trio
    competidores_nomes: Optional[List[str]] = []
    handicap_total: Optional[int] = None
    
    class Config:
        from_attributes = True

class EstatisticasPassadas(BaseModel):
    """Estatísticas gerais de passadas"""
    total_passadas: int = 0
    passadas_executadas: int = 0
    passadas_no_time: int = 0
    passadas_pendentes: int = 0
    colocacao_passada: Optional[int] = None
    tempo_medio_geral: Optional[float] = None
    melhor_tempo_geral: Optional[float] = None
    pior_tempo_geral: Optional[float] = None
    
    # Distribuições
    distribuicao_tempos: Dict[str, int] = {}
    distribuicao_status: Dict[str, int] = {}
    distribuicao_bois: Dict[int, int] = {}
    
    # Por categoria/prova
    por_categoria: Dict[str, Any] = {}
    por_prova: Dict[str, Any] = {}
    
    class Config:
        from_attributes = True

# ----- Modelos de Operações -----

class CriarPassadasLoteRequest(BaseModel):
    """Modelo para criar passadas em lote"""
    trio_id: int = Field(..., description="ID do trio")
    quantidade_passadas: int = Field(1, ge=1, le=20, description="Quantidade de passadas a criar")
    auto_numerar: bool = Field(True, description="Numerar automaticamente")
    tempo_limite: Optional[float] = Field(None, ge=10, decimal_places=3)
    bois_predefinidos: Optional[List[int]] = Field(None, description="Bois pré-definidos por passada")
    
    @validator('bois_predefinidos')
    def validar_bois_predefinidos(cls, v, values):
        if v is not None:
            quantidade = values.get('quantidade_passadas', 1)
            if len(v) != quantidade:
                raise ValueError('Quantidade de bois deve corresponder à quantidade de passadas')
        return v
    
    class Config:
        from_attributes = True

class RegistrarTempoRequest(BaseModel):
    """Modelo para registrar tempo de uma passada"""
    passada_id: int = Field(..., description="ID da passada")
    tempo_realizado: Decimal = Field(..., ge=0, decimal_places=3, description="Tempo realizado")
    numero_boi: Optional[int] = Field(None, ge=1, le=50, description="Número do boi (se não definido)")
    observacoes: Optional[str] = Field(None, description="Observações da execução")
    calcular_pontos: bool = Field(True, description="Calcular pontos automaticamente")
    is_sat: bool = Field(False, description="Passada SAT")
    motivo_sat: Optional[str] = Field(None, description="Motivo SAT")
    desclassificado_por: Optional[str] = Field(None, description="Desclassificado por")

    
    class Config:
        from_attributes = True

class CalcularRankingRequest(BaseModel):
    """Modelo para calcular ranking de passadas"""
    prova_id: int = Field(..., description="ID da prova")
    categoria_id: Optional[int] = Field(None, description="ID da categoria (opcional)")
    numero_passada: Optional[int] = Field(None, description="Número da passada específica")
    tipo_ranking: str = Field('tempo', description="Tipo de ranking")
    incluir_no_time: bool = Field(False, description="Incluir passadas no time")
    
    class Config:
        from_attributes = True

class ValidarPassadaRequest(BaseModel):
    """Modelo para validar se passada pode ser executada"""
    trio_id: int = Field(..., description="ID do trio")
    numero_passada: int = Field(..., ge=1, description="Número da passada")
    numero_boi: Optional[int] = Field(None, ge=1, le=50, description="Número do boi")
    
    class Config:
        from_attributes = True

class ValidacaoPassadaResponse(BaseModel):
    """Resposta da validação de passada"""
    valida: bool
    trio_pode_competir: bool
    competidores_bloqueados: List[Dict[str, Any]] = []
    boi_disponivel: bool = True
    intervalo_respeitado: bool = True
    mensagens: List[str] = []
    restricoes: List[str] = []
    
    class Config:
        from_attributes = True

# ----- Filtros e Buscas -----

class FiltrosPassadas(BaseModel):
    """Filtros para busca de passadas"""
    trio_id: Optional[int] = None
    prova_id: Optional[int] = None
    categoria_id: Optional[int] = None
    numero_passada: Optional[int] = None
    status: Optional[str] = None
    numero_boi: Optional[int] = None
    tempo_min: Optional[float] = None
    tempo_max: Optional[float] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    competidor_id: Optional[int] = None
    apenas_executadas: bool = False
    
    # Paginação
    pagina: int = Field(1, ge=1)
    tamanho_pagina: int = Field(25, ge=5, le=1000)
    
    class Config:
        from_attributes = True

class FiltrosControleParticipacao(BaseModel):
    """Filtros para controle de participação"""
    competidor_id: Optional[int] = None
    prova_id: Optional[int] = None
    categoria_id: Optional[int] = None
    apenas_ativos: bool = True
    apenas_bloqueados: bool = False
    passadas_restantes_min: Optional[int] = None
    
    class Config:
        from_attributes = True

# ----- Responses Específicos -----

class PassadaTrioCompleta(PassadaTrio):
    """Passada com informações completas"""
    trio: Optional[Dict[str, Any]] = None
    prova: Optional[Dict[str, Any]] = None
    categoria: Optional[Dict[str, Any]] = None
    competidores: List[Dict[str, Any]] = []
    
    # Posições no ranking
    posicao_tempo: Optional[int] = None
    posicao_pontos: Optional[int] = None
    
    # Controle de participação
    controles_participacao: List[ControleParticipacao] = []
    
    class Config:
        from_attributes = True

class RelatorioPassadas(BaseModel):
    """Relatório completo de passadas"""
    prova: Dict[str, Any]
    categoria: Optional[Dict[str, Any]] = None
    configuracao: Optional[ConfiguracaoPassadas] = None

# ----- Validadores customizados -----

@field_validator('estado')
def validar_estado(cls, v):
    if v and len(v) != 2:
        raise ValueError('Estado deve ter exatamente 2 caracteres')
    return v.upper() if v else v