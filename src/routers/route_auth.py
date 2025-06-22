from fastapi import APIRouter, status, Depends, Form, HTTPException, Query, Header
from sqlalchemy.orm import Session
from src.utils.auth_utils import obter_usuario_logado
from src.database.db import get_db
from src.database import models
from src.repositorios.usuario import RepositorioUsuario

from datetime import datetime, timedelta
from typing import Optional

from src.providers import hash_provider, token_provider
from src.utils.route_error_handler import RouteErrorHandler
from jose import jwt, JWTError  # Adicionar JWTError aqui
from src.utils.api_response import success_response, error_response

from fastapi.security import OAuth2PasswordRequestForm
import re
router = APIRouter(tags=['Auth'], route_class=RouteErrorHandler)

@router.post("/login", status_code=status.HTTP_200_OK)
async def efetuar_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session= Depends(get_db)):
    no_email = form_data.username
    no_senha = form_data.password
    client_id = form_data.client_id
    
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    cpf_regex = r'^\d{11}$'
    
    if re.match(email_regex, no_email):
        usuario = await RepositorioUsuario(db).get_by_email(no_email)
    elif re.match(cpf_regex, no_email):
        usuario = await RepositorioUsuario(db).get_by_cpf(no_email)
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
    token = await token_provider.gerar_access_token({'sub': usuario.no_email, 'client_id':client_id})

    #return success_response(message='Usuário logado com sucesso!', data={'usuario':usuario, 'access_token':token})
    return models.LoginSucesso(usuario=usuario, access_token=token)

@router.get("/gerar-api-token/{api_name}", status_code=status.HTTP_200_OK)
async def gerar_api_token(api_name: str):
    if api_name != 'api-whatsapp':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'O nome da API informado não foi aceito!')
    token = await token_provider.gerar_api_token({'sub': api_name})
    return token

@router.post("/me", response_model=models.UsuarioLista, status_code=status.HTTP_200_OK)
async def obter_usuario(usuario: models.Usuario = Depends(obter_usuario_logado)):
    return usuario

@router.post("/token/api", status_code=status.HTTP_200_OK)
async def gerar_token_api(
    api_key: str = Header(..., description="Chave de API para autenticação"),
    scope: Optional[str] = Form(None, description="Escopo de acesso solicitado")
):
    # Lista de chaves de API válidas (em produção, use ambiente seguro)
    VALID_API_KEYS = ["talkcare_api_key_1", "talkcare_api_key_2"]
    
    if api_key not in VALID_API_KEYS:
        return error_response(message='Chave de API inválida!')
    
    # Definir permissões com base no escopo solicitado
    permissoes = ["read:basic"]
    if scope == "full":
        permissoes.extend(["write:data", "delete:data"])
    
    # Criar payload para o token
    payload = {
        'sub': api_key,
        'permissoes': permissoes,
        'tipo_token': 'api',
        'exp': datetime.utcnow() + timedelta(hours=24)  # Expira em 24 horas
    }
    
    # Gerar o token
    token = await token_provider.gerar_access_token(payload)
    
    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 86400,  # 24 horas em segundos
        "scope": scope or "basic",
        "message": "Token de API gerado com sucesso."
    }

@router.post("/oauth/token", status_code=status.HTTP_200_OK)
async def gerar_oauth_token(
    grant_type: str = Form(..., description="Tipo de concessão (deve ser 'client_credentials')"),
    client_id: str = Form(..., description="ID do cliente"),
    client_secret: str = Form(..., description="Segredo do cliente"),
    scope: Optional[str] = Form(None, description="Escopo de acesso solicitado")
):
    # Verificar tipo de concessão
    if grant_type != "client_credentials":
        return error_response(message='Tipo de concessão inválido. Use "client_credentials"')
    
    # Em produção, essas credenciais devem ser armazenadas de forma segura
    VALID_CLIENTS = {
        "talkcare_client_1": "secret1",
        "talkcare_client_2": "secret2"
    }
    
    # Verificar credenciais do cliente
    if client_id not in VALID_CLIENTS or VALID_CLIENTS[client_id] != client_secret:
        return error_response(message='Credenciais de cliente inválidas!')
    
    # Definir permissões com base no escopo solicitado
    permissoes = ["read:basic"]
    if scope:
        permissoes.extend(scope.split())
    
    # Criar payload para o token
    payload = {
        'sub': f'client_{client_id}',
        'client_id': client_id,
        'permissoes': permissoes,
        'tipo_token': 'client_credentials',
        'exp': datetime.utcnow() + timedelta(hours=12)  # Expira em 12 horas
    }
    
    # Gerar o token
    token = await token_provider.gerar_access_token(payload)
    
    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 43200,  # 12 horas em segundos
        "scope": scope or "read:basic",
        "message": "Token de cliente gerado com sucesso."
    }