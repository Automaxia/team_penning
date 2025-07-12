from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.orm import Session
from jose import JWTError
from fastapi.security import OAuth2PasswordBearer
from src.providers import token_provider
from src.database.models import Usuario
from src.repositorios.usuario import RepositorioUsuario
from src.database.db import get_db
from typing import Union, Dict, Any, Optional
from jose.exceptions import JWTError
from src.utils.route_error_handler import RouteErrorHandler
from fastapi.security import OAuth2PasswordRequestForm
from src.database import models
from src.utils.api_response import success_response, error_response
from src.providers import hash_provider, token_provider

# Configuração para permitir uso sem autenticação
PERMITIR_ACESSO_SEM_LOGIN = True  # Altere para False quando quiser exigir login

oauth2_schema = OAuth2PasswordBearer(tokenUrl='/login', auto_error=False)  # auto_error=False permite token opcional

router = APIRouter(route_class=RouteErrorHandler)

@router.post("/login", status_code=status.HTTP_200_OK)
async def efetuar_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session= Depends(get_db)):
    no_login = form_data.username
    no_senha = form_data.password
    client_id = form_data.client_id    
    
    if no_login:
        usuario = await RepositorioUsuario(db).get_by_login(no_login)
    else:
        return error_response(message='O USUÁRIO informado não é um email ou CPF válido!')
    
    if not usuario:
        #raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'O USUÁRIO informado não encontrado!')
        return error_response(message='O USUÁRIO informado não encontrado!')
    
    senha_valida = await hash_provider.verifica_hash(no_senha, usuario.no_senha)
    if not senha_valida:
        #raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'A SENHA informada não encontrada!')
        return error_response(message='A SENHA informada não encontrada!')

    # Gerando Token JWT
    token = await token_provider.gerar_access_token({'sub': usuario.no_login, 'client_id':client_id})

    #return success_response(message='Usuário logado com sucesso!', data={'usuario':usuario, 'access_token':token})
    return models.LoginSucesso(usuario=usuario, access_token=token)

async def obter_usuario_logado(token: Optional[str] = Depends(oauth2_schema), db: Session = Depends(get_db)) -> Union[Usuario, bool, Dict[str, Any]]:
    """
    Função para obter usuário logado ou retornar usuário fictício se configurado
    """
    
    # Se não há token e acesso sem login está permitido, retorna usuário fictício
    if not token and PERMITIR_ACESSO_SEM_LOGIN:
        return _criar_usuario_ficticio()
    
    # Se não há token e acesso sem login NÃO está permitido, retorna erro
    if not token and not PERMITIR_ACESSO_SEM_LOGIN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token de acesso obrigatório',
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        # Verifica o token
        payload = await token_provider.verificar_access_token(token)

        # Token de API ou cliente OAuth
        if isinstance(payload, dict):
            tipo_token = payload.get('tipo_token')
            
            if tipo_token in ['api', 'client_credentials']:
                return {
                    'sq_usuario': -3,
                    'no_nome': f"API Access ({payload.get('client_id', 'unknown')})",
                    'no_email': f"{tipo_token}@teampenning.ai",
                    'nu_cpf': 'api',
                    'bo_status': True,
                    'eh_api': True,
                    'permissoes': payload.get('permissoes', ['read:basic']),
                    'client_id': payload.get('client_id', 'unknown')
                }
            
            # Token inicial
            if tipo_token == 'inicial':
                return {
                    'sq_usuario': -1,
                    'no_nome': 'Acesso Inicial',
                    'no_email': 'inicial@teampenning.ai',
                    'nu_cpf': 'inicial',
                    'bo_status': True,
                    'eh_inicial': True,
                    'permissoes': payload.get('permissoes', ['read:basic']),
                    'client_id': payload.get('client_id', 'inicial')
                }

        # Token de API WhatsApp
        if payload in ['api-whatsapp', 'teampenning_api_key_1']:
            return True
            
        # Token normal - buscar usuário no banco
        no_email = payload['sub'] if isinstance(payload, dict) else payload
        
        if no_email == 'expirou':
            if PERMITIR_ACESSO_SEM_LOGIN:
                return _criar_usuario_ficticio()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token expirou',
                headers={"WWW-Authenticate": "Bearer"}
            )

        if not no_email:
            if PERMITIR_ACESSO_SEM_LOGIN:
                return _criar_usuario_ficticio()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token inválido, email não encontrado',
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Buscar usuário no banco
        usuario = await RepositorioUsuario(db).get_by_email(no_email)
        if not usuario:
            if PERMITIR_ACESSO_SEM_LOGIN:
                return _criar_usuario_ficticio()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token inválido, usuário não encontrado',
                headers={"WWW-Authenticate": "Bearer"}
            )

        return usuario

    except (JWTError, Exception) as e:
        # Se há erro no token e acesso sem login está permitido, retorna usuário fictício
        if PERMITIR_ACESSO_SEM_LOGIN:
            return _criar_usuario_ficticio()
        
        # Caso contrário, retorna erro de autenticação
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token inválido',
            headers={"WWW-Authenticate": "Bearer"}
        )


def _criar_usuario_ficticio() -> Dict[str, Any]:
    """
    Cria um usuário fictício para permitir acesso sem autenticação
    """
    return {
        'sq_usuario': -999,
        'no_nome': 'Usuário Público',
        'no_email': 'publico@teampenning.ai',
        'nu_cpf': 'publico',
        'bo_status': True,
        'eh_publico': True,
        'eh_ficticio': True,
        'permissoes': [
            'read:basic', 
            'read:competidores', 
            'read:categorias', 
            'read:provas', 
            'read:trios', 
            'read:resultados', 
            'read:pontuacao',
            'export:dados'
        ],
        'client_id': 'publico'
    }


# Dependência alternativa que sempre permite acesso
async def obter_usuario_publico(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Dependência que sempre retorna um usuário público, sem verificar autenticação
    Use esta dependência quando quiser permitir acesso total sem login
    """
    return _criar_usuario_ficticio()


# Dependência opcional que tenta autenticar mas não falha
async def obter_usuario_opcional(token: Optional[str] = Depends(oauth2_schema), db: Session = Depends(get_db)) -> Union[Usuario, Dict[str, Any]]:
    """
    Dependência que tenta autenticar o usuário, mas se falhar retorna usuário público
    Use quando quiser dar privilégios extras para usuários logados, mas permitir acesso básico para todos
    """
    if not token:
        return _criar_usuario_ficticio()
    
    try:
        return await obter_usuario_logado(token, db)
    except HTTPException:
        return _criar_usuario_ficticio()


async def verificar_permissao_inicial(usuario, permissao_necessaria: str) -> bool:
    """
    Verifica se um usuário inicial tem a permissão necessária
    """
    # Se for o token da API WhatsApp, concede todas as permissões
    if usuario is True:
        return True
        
    # Se for um usuário inicial, fictício ou público, verifica as permissões
    if isinstance(usuario, dict):
        if usuario.get('eh_inicial') or usuario.get('eh_ficticio') or usuario.get('eh_publico'):
            permissoes = usuario.get('permissoes', [])
            return permissao_necessaria in permissoes
        
        # Usuário de API
        if usuario.get('eh_api'):
            permissoes = usuario.get('permissoes', [])
            return permissao_necessaria in permissoes
            
    # Caso contrário, é um usuário normal e tem todas as permissões
    return True


async def requer_permissao(permissao: str, usuario = Depends(obter_usuario_logado)):
    """
    Dependência para proteger rotas que precisam de permissões específicas
    """
    tem_permissao = await verificar_permissao_inicial(usuario, permissao)
    
    if not tem_permissao:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permissão insuficiente. Necessária: {permissao}"
        )
    
    return True


# Funcções auxiliares para configuração
def habilitar_acesso_publico():
    """Habilita acesso público sem autenticação"""
    global PERMITIR_ACESSO_SEM_LOGIN
    PERMITIR_ACESSO_SEM_LOGIN = True


def desabilitar_acesso_publico():
    """Desabilita acesso público, exigindo autenticação"""
    global PERMITIR_ACESSO_SEM_LOGIN
    PERMITIR_ACESSO_SEM_LOGIN = False


def status_acesso_publico() -> bool:
    """Retorna se o acesso público está habilitado"""
    return PERMITIR_ACESSO_SEM_LOGIN