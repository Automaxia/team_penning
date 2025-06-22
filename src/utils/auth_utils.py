from fastapi import status, Depends, HTTPException
from sqlalchemy.orm import Session
from jose import JWTError
from fastapi.security import OAuth2PasswordBearer
from src.providers import token_provider
from src.database.models import Usuario
from src.repositorios.usuario import RepositorioUsuario
from src.database.db import get_db
from typing import Union, Dict, Any
# Add this import at the top of token_provider.py
from jose.exceptions import JWTError

oauth2_schema = OAuth2PasswordBearer(tokenUrl='/login')

async def obter_usuario_logado(token: str = Depends(oauth2_schema), db: Session=Depends(get_db)) -> Union[Usuario, bool, Dict[str, Any]]:

    try:
        payload = await token_provider.verificar_access_token(token)

        if isinstance(payload, dict):
            # Verificar se é token de API ou cliente OAuth
            tipo_token = payload.get('tipo_token')
            if tipo_token in ['api', 'client_credentials']:
                return {
                    'sq_usuario': -3,
                    'no_nome': f"API Access ({payload.get('client_id', 'unknown')})",
                    'no_email': f"{tipo_token}@talkcare.ai",
                    'nu_cpf': 'api',
                    'bo_status': True,
                    'eh_api': True,
                    'permissoes': payload.get('permissoes', ['read:basic']),
                    'client_id': payload.get('client_id', 'unknown')
                }
        # Verifica se é token de API WhatsApp
        if payload in ['api-whatsapp', 'talkcare_api_key_1']:
            return True
            
        # Verifica se é token inicial
        if isinstance(payload, dict) and payload.get('tipo_token') == 'inicial':
            # Cria um objeto simples para representar o usuário inicial
            usuario_inicial = {
                'sq_usuario': -1,
                'no_nome': 'Acesso Inicial',
                'no_email': 'inicial@talkcare.ai',
                'nu_cpf': 'inicial',
                'bo_status': True,
                'eh_inicial': True,
                'permissoes': payload.get('permissoes', ['read:basic']),
                'client_id': payload.get('client_id', 'inicial')
            }
            return usuario_inicial
            
        # Se for token normal, continua o fluxo padrão
        no_email = payload['sub'] if isinstance(payload, dict) else payload
        
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token inválido', headers={"WWW-Authenticate": "Bearer"})

    if no_email == 'expirou':
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token expirou', headers={"WWW-Authenticate": "Bearer"})

    if not no_email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token inválido, CPF não encontrado', headers={"WWW-Authenticate": "Bearer"})
    
    usuario = await RepositorioUsuario(db).get_by_email(no_email)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token inválido, Usuário não encontrado', headers={"WWW-Authenticate": "Bearer"})

    return usuario


async def verificar_permissao_inicial(usuario, permissao_necessaria: str) -> bool:
    """
    Verifica se um usuário inicial tem a permissão necessária
    """
    # Se for o token da API WhatsApp, concede todas as permissões
    if usuario is True:
        return True
        
    # Se for um usuário inicial (dicionário), verifica as permissões
    if isinstance(usuario, dict) and usuario.get('eh_inicial'):
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