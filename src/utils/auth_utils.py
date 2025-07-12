# auth_utils.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.database.db import get_db
from src.database import schemas
from src.providers import token_provider
from typing import Optional, Union, Dict, Any

from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt

# Contexto para criptografia de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Chave secreta (deve ser segura e protegida em produção)
SECRET_KEY = "sua_chave_secreta_segura"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Security scheme
security = HTTPBearer()

# ---------------------- Dependências de Autenticação ----------------------

async def obter_token_atual(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extrai token do cabeçalho de autorização"""
    return credentials.credentials
    

async def obter_usuario_logado(
    token: str = Depends(obter_token_atual),
    db: Session = Depends(get_db)
) -> Union[schemas.Usuarios, Dict[str, Any]]:
    """Obtém o usuário atualmente logado baseado no token JWT"""
    try:
        # Verificar token usando o provider existente
        payload = await token_provider.verificar_access_token(token)
        
        # Verificar se token expirou
        if payload == 'expirou':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verificar se é token de API (compatibilidade com sistema existente)
        if isinstance(payload, dict):
            tipo_token = payload.get('tipo_token')
            if tipo_token in ['api', 'client_credentials']:
                return {
                    'sq_usuario': -3,
                    'no_nome': f"API Access ({payload.get('client_id', 'unknown')})",
                    'no_email': f"{tipo_token}@lctp.ai",
                    'nu_cpf': 'api',
                    'no_login': payload.get('sub', 'api'),
                    'bo_status': True,
                    'competidor_id': None,
                    'eh_api': True,
                    'permissoes': payload.get('permissoes', ['read:basic']),
                    'client_id': payload.get('client_id', 'unknown')
                }
        
        # Verificar se é token da API WhatsApp (compatibilidade)
        if payload in ['api-whatsapp', 'api-lctp']:
            return {
                'sq_usuario': -2,
                'no_nome': 'API WhatsApp/LCTP',
                'no_email': 'api@lctp.ai',
                'nu_cpf': 'api',
                'no_login': payload,
                'bo_status': True,
                'competidor_id': None,
                'eh_api': True
            }
        
        # Token normal - buscar usuário no banco
        login_usuario = payload if isinstance(payload, str) else payload.get('sub')
        
        if not login_usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Login não encontrado no token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Buscar usuário por login
        usuario = db.query(schemas.Usuarios).filter(
            schemas.Usuarios.no_login == login_usuario,
            schemas.Usuarios.bo_status == True
        ).first()
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return usuario
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Erro na autenticação",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def verificar_admin(
    usuario_atual = Depends(obter_usuario_logado)
) -> Union[schemas.Usuarios, Dict[str, Any]]:
    """Verifica se o usuário atual é administrador"""
    
    # Se for token de API, permitir acesso
    if isinstance(usuario_atual, dict) and usuario_atual.get('eh_api'):
        return usuario_atual
    
    # Se for usuário normal, verificar se é admin
    if hasattr(usuario_atual, 'competidor_id') and usuario_atual.competidor_id is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores"
        )
    
    return usuario_atual

async def verificar_usuario_ou_admin(
    usuario_id: int,
    usuario_atual = Depends(obter_usuario_logado)
) -> Union[schemas.Usuarios, Dict[str, Any]]:
    """Verifica se o usuário atual é o próprio usuário ou um administrador"""
    
    # Se for token de API, permitir acesso
    if isinstance(usuario_atual, dict) and usuario_atual.get('eh_api'):
        return usuario_atual
    
    # Se for usuário normal, verificar permissões
    if hasattr(usuario_atual, 'sq_usuario'):
        if usuario_atual.sq_usuario != usuario_id and usuario_atual.competidor_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: você só pode acessar seus próprios dados"
            )
    
    return usuario_atual

# ---------------------- Utilitários de Permissão ----------------------

def verificar_permissao_competidor(
    competidor_id: int,
    usuario_atual: Union[schemas.Usuarios, Dict[str, Any]]
) -> bool:
    """Verifica se o usuário tem permissão para acessar dados de um competidor"""
    
    # Se for token de API, permitir acesso
    if isinstance(usuario_atual, dict) and usuario_atual.get('eh_api'):
        return True
    
    # Admin sempre tem acesso
    if hasattr(usuario_atual, 'competidor_id') and usuario_atual.competidor_id is None:
        return True
    
    # Usuário só pode acessar seus próprios dados
    if hasattr(usuario_atual, 'competidor_id'):
        return usuario_atual.competidor_id == competidor_id
    
    return False

def is_admin(usuario: Union[schemas.Usuarios, Dict[str, Any]]) -> bool:
    """Verifica se o usuário é administrador"""
    
    # Tokens de API são considerados admin
    if isinstance(usuario, dict) and usuario.get('eh_api'):
        return True
    
    # Usuários sem competidor_id são admin
    if hasattr(usuario, 'competidor_id'):
        return usuario.competidor_id is None
    
    return False

def get_usuario_nome(usuario: Union[schemas.Usuarios, Dict[str, Any]]) -> str:
    """Obtém nome para exibição do usuário"""
    
    if isinstance(usuario, dict):
        return usuario.get('no_nome', 'API User')
    
    if hasattr(usuario, 'competidor') and usuario.competidor and usuario.competidor.nome:
        return usuario.competidor.nome
    
    if hasattr(usuario, 'no_nome'):
        return usuario.no_nome
    
    if hasattr(usuario, 'no_login'):
        return usuario.no_login
    
    return 'Usuário'

# ---------------------- Middleware de Autenticação Opcional ----------------------

async def obter_usuario_opcional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[Union[schemas.Usuarios, Dict[str, Any]]]:
    """Obtém usuário se token for fornecido, mas não falha se não for"""
    if not credentials:
        return None
    
    try:
        return await obter_usuario_logado(credentials.credentials, db)
    except HTTPException:
        return None

# ---------------------- Validadores de Contexto ----------------------

class ContextoAutenticacao:
    """Classe para gerenciar contexto de autenticação em operações"""
    
    def __init__(self, usuario: Union[schemas.Usuarios, Dict[str, Any]]):
        self.usuario = usuario
        self.is_admin = is_admin(usuario)
        
        if isinstance(usuario, dict):
            self.competidor_id = usuario.get('competidor_id')
            self.eh_api = usuario.get('eh_api', False)
        else:
            self.competidor_id = getattr(usuario, 'competidor_id', None)
            self.eh_api = False
    
    def pode_acessar_competidor(self, competidor_id: int) -> bool:
        """Verifica se pode acessar dados de um competidor específico"""
        return self.is_admin or self.competidor_id == competidor_id
    
    def pode_gerenciar_trio(self, trio) -> bool:
        """Verifica se pode gerenciar um trio específico"""
        if self.is_admin or self.eh_api:
            return True
        
        # Verificar se é integrante do trio
        if self.competidor_id and hasattr(trio, 'integrantes'):
            integrante = any(
                i.competidor_id == self.competidor_id 
                for i in trio.integrantes
            )
            return integrante
        
        return False
    
    def pode_ver_resultado(self, resultado) -> bool:
        """Verifica se pode ver resultado de uma prova"""
        # Resultados são públicos, mas pode ter lógica específica no futuro
        return True

# ---------------------- Compatibilidade com Sistema Existente ----------------------

async def verificar_permissao_inicial(usuario: Union[schemas.Usuarios, Dict[str, Any]], permissao_necessaria: str) -> bool:
    """Verifica se um usuário tem a permissão necessária (compatibilidade)"""
    
    # Tokens de API têm todas as permissões
    if isinstance(usuario, dict) and usuario.get('eh_api'):
        permissoes = usuario.get('permissoes', [])
        return permissao_necessaria in permissoes or 'read:basic' in permissoes
    
    # Usuários normais têm todas as permissões
    return True

async def requer_permissao(permissao: str, usuario = Depends(obter_usuario_logado)):
    """Dependência para proteger rotas que precisam de permissões específicas"""
    tem_permissao = await verificar_permissao_inicial(usuario, permissao)
    
    if not tem_permissao:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permissão insuficiente. Necessária: {permissao}"
        )
    
    return True

def gerar_hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)

def verificar_senha(senha: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha, senha_hash)

def gerar_token_acesso(dados: dict, tempo_expiracao: timedelta = None):
    to_encode = dados.copy()
    expire = datetime.utcnow() + (tempo_expiracao or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)