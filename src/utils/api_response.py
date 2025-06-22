from typing import Any, Dict, List, Optional, TypeVar, Union
from src.database.models import ApiResponse
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm.decl_api import DeclarativeBase
from sqlalchemy.engine.row import Row

T = TypeVar("T")

def sqlalchemy_to_dict(obj):
    """
    Converte um objeto SQLAlchemy em um dicionário serializável.
    Suporta tanto objetos ORM quanto tuplas de queries diretas.
    """
    if isinstance(obj, Row):
        # Se for uma tupla retornada por fetchone(), converter em dicionário
        return dict(obj._mapping)

    if hasattr(obj, '__table__'):
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    
    return obj

def is_sqlalchemy_model(obj):
    """
    Verifica se um objeto é um modelo SQLAlchemy.
    """
    try:
        return hasattr(obj, '__tablename__') and hasattr(obj, '__table__')
    except:
        return False

def serialize_data(data):
    """
    Serializa dados, convertendo objetos SQLAlchemy e tuplas de queries em dicionários.
    """
    if data is None:
        return None
    
    # Se for uma lista
    if isinstance(data, list):
        return [serialize_data(item) for item in data]
    
    # Se for um SQLAlchemy model ou uma tupla do SQLAlchemy
    if is_sqlalchemy_model(data) or isinstance(data, Row):
        return sqlalchemy_to_dict(data)
    
    # Se for um dicionário, serializar valores internos
    if isinstance(data, dict):
        return {k: serialize_data(v) for k, v in data.items()}
    
    # Para outros tipos, retorna o próprio objeto
    return data

def create_response(
    success: bool, 
    data: Optional[Union[T, List[T], Dict[str, Any]]] = None, 
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200
) -> ApiResponse:
    """
    Cria uma resposta padronizada para a API, serializando automaticamente objetos SQLAlchemy.
    """
    # Serializar os dados antes de criar a resposta
    serialized_data = serialize_data(data)
    
    return ApiResponse(
        success=success,
        data=serialized_data,
        message=message,
        meta=meta,
        status_code=status_code
    )


def success_response(
    data: Optional[Union[T, List[T], Dict[str, Any]]] = None,
    message: str = "Operação realizada com sucesso",
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200
) -> ApiResponse:
    """
    Cria uma resposta de sucesso padronizada.
    
    Args:
        data: Dados a serem retornados
        message: Mensagem de sucesso
        meta: Metadados adicionais (ex: paginação)
        status_code: Código HTTP de status (padrão 200)
        
    Returns:
        Um objeto ApiResponse com o campo success=True
    """
    return create_response(True, data, message, meta, status_code)


def error_response(
    message: str = "Ocorreu um erro ao processar a solicitação",
    data: Optional[Union[T, List[T], Dict[str, Any]]] = None,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 400
) -> ApiResponse:
    """
    Cria uma resposta de erro padronizada.
    
    Args:
        message: Mensagem de erro
        data: Dados de erro adicionais (se houver)
        meta: Metadados adicionais
        status_code: Código HTTP de status (padrão 400)
        
    Returns:
        Um objeto ApiResponse com o campo success=False
    """
    return create_response(False, data, message, meta, status_code)