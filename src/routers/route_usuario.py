from fastapi import APIRouter, status, Depends, HTTPException, Path, Query, Body
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, date
from src.utils.auth_utils import obter_usuario_logado, verificar_admin
from src.database.db import get_db
from src.database import models, schemas
from src.utils.api_response import success_response, error_response
from src.repositorios.usuario import RepositorioUsuario
from src.utils.route_error_handler import RouteErrorHandler

router = APIRouter(route_class=RouteErrorHandler)

# -------------------------- Rotas Básicas de Usuários (Admin) --------------------------

@router.get("/usuario/pesquisar", tags=['Usuário'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def pesquisar_usuarios(
    nome: Optional[str] = Query(default=None, max_length=300, description="Nome do usuário"),
    login: Optional[str] = Query(default=None, max_length=50, description="Login do usuário"),
    email: Optional[str] = Query(default=None, max_length=300, description="Email do usuário"),
    ativo: Optional[bool] = Query(default=True, description="Status ativo do usuário"),
    is_admin: Optional[bool] = Query(default=None, description="Se é administrador"),
    pagina: Optional[int] = Query(default=0, ge=0, description="Número da página"),
    tamanho_pagina: Optional[int] = Query(default=0, ge=0, description="Tamanho da página"),
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Pesquisa usuários com filtros diversos (apenas administradores)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        usuarios = await repo_usuario.get_all(
            nome=nome,
            login=login,
            email=email,
            ativo=ativo,
            is_admin=is_admin,
            pagina=pagina,
            tamanho_pagina=tamanho_pagina
        )
        
        if not usuarios:
            return error_response(message='Nenhum usuário encontrado com os filtros informados!')
        
        return success_response(
            data=[models.UsuarioLista.from_orm(u) for u in usuarios]
        )
        
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

@router.post("/usuario/criar", tags=['Usuário'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def criar_usuario(
    usuario: models.UsuarioPOST,
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Cria um novo usuário (apenas administradores)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        # Validar dados antes de criar
        erros = await repo_usuario.validar_dados_usuario(usuario.dict())
        if erros:
            return error_response(
                message="Erros de validação encontrados",
                data={"erros": erros},
                status_code=400
            )
        
        novo_usuario = await repo_usuario.post(usuario)
        
        return success_response(
            data=models.UsuarioCompleto.from_orm(novo_usuario),
            message='Usuário criado com sucesso',
            status_code=201
        )
        
    except ValueError as e:
        return error_response(message=str(e), status_code=400)
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

@router.put("/usuario/atualizar/{usuario_id}", tags=['Usuário'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def atualizar_usuario(
    usuario_id: int = Path(..., description="ID do usuário"),
    usuario: models.UsuarioPUT = Body(...),
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Atualiza dados de um usuário (apenas administradores)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        # Verificar se o usuário existe
        usuario_existente = await repo_usuario.get_by_id(usuario_id)
        if not usuario_existente:
            return error_response(message='Usuário não encontrado!')
        
        # Validar dados antes de atualizar
        erros = await repo_usuario.validar_dados_usuario(usuario.dict(exclude_unset=True), usuario_id)
        if erros:
            return error_response(
                message="Erros de validação encontrados",
                data={"erros": erros},
                status_code=400
            )
        
        usuario_atualizado = await repo_usuario.put(usuario_id, usuario)
        
        return success_response(
            data=models.UsuarioCompleto.from_orm(usuario_atualizado),
            message='Usuário atualizado com sucesso'
        )
        
    except ValueError as e:
        return error_response(message=str(e), status_code=400)
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

@router.post("/usuario/cadastro-publico", tags=["Usuário"], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def cadastro_publico_usuario(
    dados: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Cria um novo competidor e um novo usuário associado (uso público).
    """
    try:
        from src.repositorios.usuario import RepositorioUsuario
        from src.repositorios.competidor import RepositorioCompetidor

        # Criar competidor
        competidor_dados = models.CompetidorPOST(**dados)
        competidor = await RepositorioCompetidor(db).post(competidor_dados)

        # Criar usuário
        usuario_dados = models.UsuarioPOST(
            nu_cpf=dados.get("nu_cpf"),
            no_nome=dados["nome"],
            no_login=dados.get("login"),
            no_senha=dados.get("senha"),
            no_email=dados.get("email"),
            competidor_id=competidor.id
        )
        usuario = await RepositorioUsuario(db).post(usuario_dados)

        return success_response(
            data={"usuario_id": usuario.sq_usuario, "competidor_id": competidor.id},
            message="Cadastro realizado com sucesso"
        )

    except Exception as e:
        return error_response(message=str(e))


@router.get("/usuario/consultar/{usuario_id}", tags=['Usuário'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def consultar_usuario(
    usuario_id: int = Path(..., description="ID do usuário"),
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Consulta um usuário específico por ID (apenas administradores)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        usuario = await repo_usuario.get_by_id(usuario_id)
        if not usuario:
            return error_response(message='Usuário não encontrado!')
        
        return success_response(
            data=models.UsuarioCompleto.from_orm(usuario)
        )
        
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

@router.delete("/usuario/deletar/{usuario_id}", tags=['Usuário'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def excluir_usuario(
    usuario_id: int = Path(..., description="ID do usuário"),
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Realiza exclusão lógica de um usuário (apenas administradores)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        # Verificar se o usuário existe
        usuario = await repo_usuario.get_by_id(usuario_id)
        if not usuario:
            return error_response(message='Usuário não encontrado!')
        
        # Não permitir excluir o próprio usuário
        if usuario_id == usuario_atual.sq_usuario:
            return error_response(message='Não é possível excluir seu próprio usuário!')
        
        await repo_usuario.delete(usuario_id)
        
        return success_response(
            data=None,
            message='Usuário excluído com sucesso'
        )
        
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

# -------------------------- Gerenciamento de Perfis --------------------------

@router.get("/usuario/perfil/{usuario_id}", tags=['Perfil'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def obter_perfil_usuario(
    usuario_id: int = Path(..., description="ID do usuário"),
    db: Session = Depends(get_db),
    usuario_atual = Depends(obter_usuario_logado)
):
    """Obtém perfil de um usuário (próprio usuário ou admin)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        # Verificar permissões
        if usuario_id != usuario_atual.sq_usuario and usuario_atual.competidor_id is not None:
            return error_response(
                message='Você só pode visualizar seu próprio perfil!',
                status_code=403
            )
        
        perfil = await repo_usuario.get_perfil_usuario(usuario_id)
        if not perfil:
            return error_response(message='Usuário não encontrado!')
        
        return success_response(
            data=models.PerfilUsuario(**perfil)
        )
        
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

# -------------------------- Administração de Usuários --------------------------

@router.put("/usuario/promover-admin/{usuario_id}", tags=['Administração'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def promover_para_admin(
    usuario_id: int = Path(..., description="ID do usuário"),
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Promove usuário para administrador (apenas administradores)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        # Verificar se o usuário existe
        usuario = await repo_usuario.get_by_id(usuario_id)
        if not usuario:
            return error_response(message='Usuário não encontrado!')
        
        if usuario.competidor_id is None:
            return error_response(message='Usuário já é administrador!')
        
        usuario_atualizado = await repo_usuario.promover_para_admin(usuario_id)
        
        return success_response(
            data=models.UsuarioCompleto.from_orm(usuario_atualizado),
            message='Usuário promovido para administrador com sucesso'
        )
        
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

@router.put("/usuario/associar-competidor/{usuario_id}/{competidor_id}", tags=['Administração'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def associar_competidor(
    usuario_id: int = Path(..., description="ID do usuário"),
    competidor_id: int = Path(..., description="ID do competidor"),
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Associa usuário a um competidor (apenas administradores)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        # Verificar se o usuário existe
        usuario = await repo_usuario.get_by_id(usuario_id)
        if not usuario:
            return error_response(message='Usuário não encontrado!')
        
        usuario_atualizado = await repo_usuario.associar_competidor(usuario_id, competidor_id)
        
        return success_response(
            data=models.UsuarioCompleto.from_orm(usuario_atualizado),
            message='Competidor associado ao usuário com sucesso'
        )
        
    except ValueError as e:
        return error_response(message=str(e), status_code=400)
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

@router.put("/usuario/resetar-senha/{usuario_id}", tags=['Administração'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def resetar_senha_usuario(
    usuario_id: int = Path(..., description="ID do usuário"),
    nova_senha: str = Body(..., min_length=6, description="Nova senha"),
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Reseta senha de um usuário (apenas administradores)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        # Verificar se o usuário existe
        usuario = await repo_usuario.get_by_id(usuario_id)
        if not usuario:
            return error_response(message='Usuário não encontrado!')
        
        sucesso = await repo_usuario.resetar_senha(usuario_id, nova_senha)
        
        if not sucesso:
            return error_response(message='Erro ao resetar senha!')
        
        return success_response(
            data=None,
            message='Senha resetada com sucesso'
        )
        
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

# -------------------------- Busca Avançada --------------------------

@router.post("/usuario/busca-avancada", tags=['Busca'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def busca_avancada_usuarios(
    filtros: Dict[str, Any] = Body(..., example={
        "busca_geral": "joão",
        "data_inicio": "2024-01-01",
        "data_fim": "2024-12-31",
        "tipo_usuario": "competidor",
        "status": True,
        "tem_email": True,
        "ordenar_por": "nome",
        "direcao": "asc",
        "pagina": 1,
        "tamanho_pagina": 20
    }),
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Busca avançada de usuários com múltiplos filtros (apenas administradores)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        usuarios = await repo_usuario.buscar_usuarios_avancado(filtros)
        
        if not usuarios:
            return error_response(message='Nenhum usuário encontrado com os filtros informados!')
        
        return success_response(
            data=[models.UsuarioLista.from_orm(u) for u in usuarios],
            meta={
                "total_encontrados": len(usuarios),
                "filtros_aplicados": filtros
            }
        )
        
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

# -------------------------- Operações em Lote --------------------------

@router.post("/usuario/criar-multiplos", tags=['Lote'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def criar_multiplos_usuarios(
    usuarios: List[models.UsuarioPOST] = Body(..., min_items=1),
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Cria múltiplos usuários em uma operação (apenas administradores)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        usuarios_criados = await repo_usuario.criar_multiplos_usuarios(usuarios)
        
        return success_response(
            data=[models.UsuarioCompleto.from_orm(u) for u in usuarios_criados],
            message=f'{len(usuarios_criados)} usuários criados com sucesso',
            status_code=201
        )
        
    except ValueError as e:
        return error_response(message=str(e), status_code=400)
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

@router.put("/usuario/atualizar-multiplos", tags=['Lote'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def atualizar_multiplos_usuarios(
    updates: List[Dict[str, Any]] = Body(..., example=[
        {"id": 1, "no_nome": "Novo Nome", "no_email": "novo@email.com"},
        {"id": 2, "bo_status": False}
    ]),
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Atualiza múltiplos usuários (apenas administradores)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        # Validar dados
        for update in updates:
            if 'id' not in update:
                return error_response(message='Cada item deve conter "id"!')
        
        sucesso = await repo_usuario.atualizar_multiplos_usuarios(updates)
        
        if sucesso:
            return success_response(
                data=None,
                message=f'{len(updates)} usuários atualizados com sucesso'
            )
        else:
            return error_response(message='Erro ao atualizar usuários!')
            
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

# -------------------------- Relatórios --------------------------

@router.get("/usuario/relatorio/ativos-inativos", tags=['Relatórios'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def relatorio_usuarios_status(
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Gera relatório de usuários ativos e inativos (apenas administradores)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        relatorio = await repo_usuario.relatorio_usuarios_ativos_inativos()
        
        return success_response(data=relatorio)
        
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

# -------------------------- Estatísticas --------------------------

@router.get("/usuario/estatisticas", tags=['Estatísticas'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def estatisticas_usuarios(
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Recupera estatísticas gerais dos usuários (apenas administradores)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        estatisticas = await repo_usuario.get_estatisticas_usuarios()
        
        return success_response(data=estatisticas)
        
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

# -------------------------- Utilitários --------------------------

@router.get("/usuario/opcoes/tipos", tags=['Utilitários'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_tipos_usuario(
    db: Session = Depends(get_db),
    usuario_atual = Depends(obter_usuario_logado)
):
    """Lista tipos de usuário disponíveis"""
    
    try:
        tipos = [
            {"value": "admin", "label": "Administrador"},
            {"value": "competidor", "label": "Competidor"}
        ]
        
        return success_response(data=tipos)
        
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

@router.get("/usuario/competidores-sem-usuario", tags=['Utilitários'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_competidores_sem_usuario(
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Lista competidores que não possuem usuário associado (apenas administradores)"""
    
    try:
        # Buscar competidores que não têm usuário
        competidores = db.query(schemas.Competidores).outerjoin(
            schemas.Usuarios,
            schemas.Competidores.id == schemas.Usuarios.competidor_id
        ).filter(
            schemas.Competidores.ativo == True,
            schemas.Usuarios.competidor_id.is_(None)
        ).order_by(schemas.Competidores.nome).all()
        
        if not competidores:
            return error_response(message='Todos os competidores já possuem usuário associado!')
        
        return success_response(
            data=[models.Competidor.from_orm(c) for c in competidores]
        )
        
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )

# -------------------------- Validações Dinâmicas --------------------------

@router.post("/usuario/validar-dados", tags=['Validações'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def validar_dados_usuario_dinamico(
    dados: Dict[str, Any] = Body(..., example={
        "no_login": "novo_login",
        "no_email": "email@teste.com",
        "competidor_id": 1
    }),
    excluir_usuario_id: Optional[int] = Query(default=None, description="ID do usuário a excluir da validação"),
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_admin)
):
    """Valida dados de usuário dinamicamente (apenas administradores)"""
    
    try:
        repo_usuario = RepositorioUsuario(db)
        
        erros = await repo_usuario.validar_dados_usuario(dados, excluir_usuario_id)
        
        return success_response(
            data={
                "valido": len(erros) == 0,
                "erros": erros
            },
            message="Validação concluída"
        )
        
    except Exception as e:
        return error_response(
            message=f"Erro interno do servidor: {str(e)}",
            status_code=500
        )