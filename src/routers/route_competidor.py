# route_competidor.py - VERSÃO CORRIGIDA
from fastapi import APIRouter, status, Depends, HTTPException, Path, Query, Body
from typing import List, Optional, Dict, Any
from sqlalchemy import select, distinct, func
from sqlalchemy.orm import Session
from datetime import datetime, date
from src.utils.auth_utils import obter_usuario_logado
from src.database.db import get_db
from src.database import models, schemas
from src.utils.api_response import success_response, error_response
from src.repositorios.competidor import RepositorioCompetidor
from src.utils.route_error_handler import RouteErrorHandler

router = APIRouter(route_class=RouteErrorHandler)

# -------------------------- Rotas Básicas de Competidores --------------------------

@router.get("/competidor/pesquisar", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def pesquisar_competidores(
    nome: Optional[str] = Query(default=None, max_length=300, description="Nome do competidor"),
    handicap: Optional[int] = Query(default=None, ge=0, le=7, description="Handicap do competidor"),
    cidade: Optional[str] = Query(default=None, max_length=100, description="Cidade do competidor"),
    estado: Optional[str] = Query(default=None, max_length=2, description="Estado (UF) do competidor"),
    sexo: Optional[str] = Query(default=None, regex="^[MF]$", description="Sexo do competidor (M/F)"),
    idade_min: Optional[int] = Query(default=None, ge=0, le=100, description="Idade mínima"),
    idade_max: Optional[int] = Query(default=None, ge=0, le=100, description="Idade máxima"),
    categoria_id: Optional[int] = Query(default=None, description="ID da categoria"),
    categoria_tipo: Optional[str] = Query(default=None, description="Tipo da categoria"),
    apenas_com_categoria: Optional[bool] = Query(default=None, description="Apenas com categoria definida"),
    ativo: Optional[bool] = Query(default=True, description="Status ativo do competidor"),
    pagina: Optional[int] = Query(default=0, ge=0, description="Número da página"),
    tamanho_pagina: Optional[int] = Query(default=0, ge=0, description="Tamanho da página"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Pesquisa competidores com filtros diversos incluindo categoria"""
    
    competidores = await RepositorioCompetidor(db).get_all(
        nome=nome,
        handicap=handicap, 
        cidade=cidade,
        estado=estado,
        sexo=sexo,
        idade_min=idade_min,
        idade_max=idade_max,
        categoria_id=categoria_id,
        categoria_tipo=categoria_tipo,
        apenas_com_categoria=apenas_com_categoria,
        ativo=ativo,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina
    )
    
    if not competidores:
        return error_response(message='Nenhum competidor encontrado com os filtros informados!')
    
    return success_response(competidores)

@router.post("/competidor/salvar", tags=['Competidor'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def criar_competidor(
    competidor: models.CompetidorPOST,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria um novo competidor com categoria automática se não informada"""
    
    try:
        novo_competidor = await RepositorioCompetidor(db).post(competidor)
        return success_response(novo_competidor, 'Competidor criado com sucesso', status_code=201)
    except ValueError as e:
        return error_response(message=str(e))

@router.put("/competidor/atualizar/{competidor_id:int}", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def atualizar_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    competidor: models.CompetidorPUT = Body(...),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Atualiza dados de um competidor"""
    
    # Verificar se o competidor existe
    competidor_existente = await RepositorioCompetidor(db).get_by_id(competidor_id)
    if not competidor_existente:
        return error_response(message='Competidor não encontrado!')
    
    try:
        competidor_atualizado = await RepositorioCompetidor(db).put(competidor_id, competidor)
        
        # ⭐ ADICIONAR ESTAS LINHAS APÓS A ATUALIZAÇÃO:
        # Auto-criar controles se tem categoria
        if hasattr(competidor, 'categoria_id') and competidor.categoria_id:
            try:
                await auto_criar_controles_participacao(competidor_id, competidor.categoria_id, db)
            except Exception as e:
                print(f"Aviso: Erro ao auto-criar controles: {e}")
                # Não falha a atualização por causa disso
        
        return success_response(competidor_atualizado, 'Competidor atualizado com sucesso')
    except ValueError as e:
        return error_response(message=str(e))

@router.delete("/competidor/deletar/{competidor_id:int}", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def excluir_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Realiza exclusão lógica de um competidor"""
    
    # Verificar se o competidor existe
    competidor = await RepositorioCompetidor(db).get_by_id(competidor_id)
    if not competidor:
        return error_response(message='Competidor não encontrado!')
    
    # TODO: Verificar se o competidor tem participações ativas antes de excluir
    
    await RepositorioCompetidor(db).delete(competidor_id)
    return success_response(None, 'Competidor excluído com sucesso')

# ========================== ROTAS ESPECÍFICAS PRIMEIRO ==========================

# Estatísticas gerais (deve vir antes das rotas com parâmetros)
@router.get("/competidor/estatisticas/geral", tags=['Competidor Estatísticas'], 
           status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def estatisticas_gerais(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Recupera estatísticas gerais do sistema incluindo categorias"""
    
    try:
        repo = RepositorioCompetidor(db)
        
        # Total de competidores ativos
        total_ativos = len(await repo.get_all(ativo=True))
        
        # Distribuição por handicap
        distribuicao_handicap = {}
        for h in range(8):  # 0 a 7
            competidores_h = await repo.get_by_handicap(h)
            distribuicao_handicap[f'handicap_{h}'] = len(competidores_h)
        
        # Distribuição por sexo
        femininos = await repo.get_femininos()
        masculinos = await repo.get_all(sexo='M', ativo=True)
        
        # Estatísticas por faixa etária
        faixas_etarias = {
            'baby': len(await repo.get_by_categoria_idade(0, 12)),
            'kids': len(await repo.get_by_categoria_idade(13, 17)),
            'adulto': len(await repo.get_by_categoria_idade(18, 100))
        }
        
        # Estatísticas por categoria
        stats_categoria = await repo.get_estatisticas_por_categoria()
        
        # Competidores sem categoria
        sem_categoria = await repo.get_sem_categoria()
        
        estatisticas = {
            'total_competidores': total_ativos,
            'distribuicao_handicap': distribuicao_handicap,
            'distribuicao_sexo': {
                'feminino': len(femininos),
                'masculino': len(masculinos)
            },
            'distribuicao_faixa_etaria': faixas_etarias,
            'distribuicao_categorias': stats_categoria,
            'competidores_sem_categoria': len(sem_categoria)
        }
        
        return success_response(estatisticas)
    except Exception as e:
        return error_response(message=f'Erro ao calcular estatísticas: {str(e)}')

@router.get("/competidor/estatisticas/categoria", tags=['Competidor Estatísticas'], 
           status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def estatisticas_por_categoria(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Recupera estatísticas detalhadas por categoria"""
    
    try:
        stats = await RepositorioCompetidor(db).get_estatisticas_por_categoria()
        return success_response(stats)
    except Exception as e:
        return error_response(message=f'Erro ao calcular estatísticas por categoria: {str(e)}')

@router.get("/competidor/campeoes-handicap", tags=['Competidor Ranking'], 
           status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def campeoes_por_handicap(
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Identifica campeões por handicap para Copa dos Campeões"""
    
    campeoes = await RepositorioCompetidor(db).get_campeoes_por_handicap(ano)
    if not campeoes:
        return error_response(message='Nenhum campeão encontrado!')
    
    return success_response(campeoes)

@router.get("/competidor/femininos", tags=['Competidor'], 
           status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_femininos(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista competidores do sexo feminino"""
    
    competidores = await RepositorioCompetidor(db).get_femininos()
    if not competidores:
        return error_response(message='Nenhuma competidora encontrada!')
    
    return success_response(competidores)

@router.get("/competidor/sem-categoria", tags=['Competidor Categoria'], 
           status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_sem_categoria(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista competidores sem categoria definida"""
    
    competidores = await RepositorioCompetidor(db).get_sem_categoria()
    if not competidores:
        return error_response(message='Todos os competidores possuem categoria definida!')
    
    return success_response(competidores)

@router.get("/competidor/por-faixa-etaria", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_por_faixa_etaria(
    idade_min: int = Query(..., ge=0, le=100, description="Idade mínima"),
    idade_max: int = Query(..., ge=0, le=100, description="Idade máxima"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista competidores por faixa etária"""
    
    if idade_min > idade_max:
        return error_response(message='Idade mínima não pode ser maior que a máxima!')
    
    competidores = await RepositorioCompetidor(db).get_by_categoria_idade(idade_min, idade_max)
    if not competidores:
        return error_response(message=f'Nenhum competidor encontrado na faixa etária {idade_min}-{idade_max} anos!')
    
    return success_response(competidores)

@router.post("/competidor/atualizar-categorias-automaticamente", tags=['Competidor Categoria'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def atualizar_categorias_automaticamente(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Atualiza categorias automaticamente para competidores sem categoria"""
    
    try:
        total_atualizados = await RepositorioCompetidor(db).atualizar_categorias_automaticamente()
        return success_response(
            {'total_atualizados': total_atualizados},
            f'{total_atualizados} competidores tiveram categorias atualizadas automaticamente'
        )
    except Exception as e:
        return error_response(message=str(e))

# ========================== ROTAS COM PARÂMETROS (COM CONVERSORES) ==========================

@router.get("/competidor/consultar/{competidor_id:int}", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def consultar_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Consulta um competidor específico por ID"""
    
    competidor = await RepositorioCompetidor(db).get_by_id(competidor_id)
    if not competidor:
        return error_response(message='Competidor não encontrado!')
    
    return success_response(competidor)

@router.get("/competidor/detalhes/{competidor_id:int}", tags=['Competidor'], 
           status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def detalhes_competidor_completo(
    competidor_id: int = Path(..., description="ID do competidor"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Recupera detalhes completos do competidor incluindo categoria"""
    
    repo = RepositorioCompetidor(db)
    competidor_completo = await repo.get_competidor_com_categoria(competidor_id)
    
    if not competidor_completo:
        return error_response(message='Competidor não encontrado!')
    
    return success_response(competidor_completo)

@router.get("/competidor/estatisticas/{competidor_id:int}", tags=['Competidor Ranking'], 
           status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def estatisticas_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Recupera estatísticas completas de um competidor"""
    
    # Verificar se o competidor existe
    competidor = await RepositorioCompetidor(db).get_by_id(competidor_id)
    if not competidor:
        return error_response(message='Competidor não encontrado!')
    
    estatisticas = await RepositorioCompetidor(db).get_estatisticas_competidor(competidor_id)
    if not estatisticas:
        return error_response(message='Nenhuma estatística encontrada para este competidor!')
    
    return success_response(estatisticas)

@router.get("/competidor/categoria/{categoria_id:int}", tags=['Competidor Categoria'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_por_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista competidores de uma categoria específica"""
    
    competidores = await RepositorioCompetidor(db).get_by_categoria(categoria_id)
    if not competidores:
        return error_response(message='Nenhum competidor encontrado nesta categoria!')
    
    return success_response(competidores)

@router.put("/competidor/atualizar-categoria/{competidor_id:int}", tags=['Competidor Categoria'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def atualizar_categoria_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    categoria_data: Dict[str, Any] = Body(..., example={"categoria_id": 1}),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Atualiza apenas a categoria de um competidor"""
    
    categoria_id = categoria_data.get('categoria_id')
    
    # Verificar se o competidor existe
    competidor = await RepositorioCompetidor(db).get_by_id(competidor_id)
    if not competidor:
        return error_response(message='Competidor não encontrado!')
    
    try:
        competidor_atualizado = await RepositorioCompetidor(db).atualizar_categoria(competidor_id, categoria_id)
        return success_response(competidor_atualizado, 'Categoria atualizada com sucesso')
    except Exception as e:
        return error_response(message=str(e))

@router.get("/competidor/sugerir-categoria/{competidor_id:int}", tags=['Competidor Categoria'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def sugerir_categoria_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Sugere categorias para um competidor baseado nas regras"""
    
    # Verificar se o competidor existe
    competidor = await RepositorioCompetidor(db).get_by_id(competidor_id)
    if not competidor:
        return error_response(message='Competidor não encontrado!')
    
    sugestoes = await RepositorioCompetidor(db).sugerir_categoria(competidor_id)
    if not sugestoes:
        return error_response(message='Nenhuma categoria disponível para este competidor!')
    
    return success_response(sugestoes)

@router.post("/competidor/migrar-categorias", tags=['Competidor Categoria'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def migrar_categorias_lote(
    dados: Dict[str, Any] = Body(..., example={
        "competidores_ids": [1, 2, 3],
        "categoria_destino_id": 1
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Migra múltiplos competidores para uma categoria"""
    
    competidores_ids = dados.get('competidores_ids', [])
    categoria_destino_id = dados.get('categoria_destino_id')
    
    if not competidores_ids or not categoria_destino_id:
        return error_response(message='Deve informar competidores_ids e categoria_destino_id')
    
    try:
        total_migrados = await RepositorioCompetidor(db).migrar_categorias(competidores_ids, categoria_destino_id)
        return success_response(
            {'total_migrados': total_migrados}, 
            f'{total_migrados} competidores migrados com sucesso'
        )
    except Exception as e:
        return error_response(message=str(e))

@router.get("/competidor/por-handicap/{handicap:int}", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_por_handicap(
    handicap: int = Path(..., ge=0, le=7, description="Handicap desejado"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista competidores por handicap específico"""
    
    competidores = await RepositorioCompetidor(db).get_by_handicap(handicap)
    if not competidores:
        return error_response(message=f'Nenhum competidor encontrado com handicap {handicap}!')
    
    return success_response(competidores)

@router.get("/competidor/elegivel-categoria/{categoria_id:int}", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_elegiveis_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    excluir_ids: Optional[List[int]] = Query(default=None, description="IDs de competidores a excluir"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista competidores elegíveis para uma categoria específica"""
    
    competidores = RepositorioCompetidor(db).buscar_para_trio(categoria_id, excluir_ids or [])
    if not competidores:
        return error_response(message='Nenhum competidor elegível encontrado para esta categoria!')
    
    return success_response(competidores)

@router.get("/competidor/disponiveis-prova/{prova_id:int}/{categoria_id:int}", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_disponiveis_prova(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista competidores disponíveis para uma prova (não inscritos ainda)"""
    
    competidores = await RepositorioCompetidor(db).buscar_disponiveis_para_prova(prova_id, categoria_id, False)
    if not competidores:
        return error_response(message='Nenhum competidor disponível para esta prova/categoria!')
    
    return success_response(competidores)

@router.get("/competidor/ranking/categoria/{categoria_id:int}", tags=['Competidor Ranking'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def ranking_por_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera ranking de competidores por categoria"""
    
    ranking = await RepositorioCompetidor(db).get_ranking_por_categoria(categoria_id, ano)
    if not ranking:
        return error_response(message='Nenhum dado encontrado para gerar o ranking!')
    
    return success_response(ranking)

@router.get("/competidor/performance/{competidor_id:int}", tags=['Competidor Ranking'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def analise_performance(
    competidor_id: int = Path(..., description="ID do competidor"),
    limite_provas: int = Query(default=10, ge=1, le=50, description="Número de provas para análise"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Analisa tendências de performance do competidor"""
    
    # Verificar se o competidor existe
    competidor = await RepositorioCompetidor(db).get_by_id(competidor_id)
    if not competidor:
        return error_response(message='Competidor não encontrado!')
    
    analise = await RepositorioCompetidor(db).get_performance_trends(competidor_id, limite_provas)
    if not analise:
        return error_response(message='Nenhum dado de performance encontrado para este competidor!')
    
    return success_response(analise)

@router.get("/competidor/sugestoes-trio/{competidor_id:int}/{categoria_id:int}", tags=['Competidor Trio'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def sugestoes_trio(
    competidor_id: int = Path(..., description="ID do competidor base"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Sugere competidores compatíveis para formar trio"""
    
    # Verificar se o competidor existe
    competidor = await RepositorioCompetidor(db).get_by_id(competidor_id)
    if not competidor:
        return error_response(message='Competidor não encontrado!')
    
    sugestoes = await RepositorioCompetidor(db).get_compatibilidade_trio(competidor_id, categoria_id)
    if not sugestoes:
        return error_response(message='Nenhuma sugestão de trio encontrada!')
    
    return success_response(sugestoes)

@router.get("/competidor/historico-handicap/{competidor_id:int}", tags=['Competidor Relatórios'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def historico_handicap(
    competidor_id: int = Path(..., description="ID do competidor"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Recupera histórico de mudanças de handicap"""
    
    # Verificar se o competidor existe
    competidor = await RepositorioCompetidor(db).get_by_id(competidor_id)
    if not competidor:
        return error_response(message='Competidor não encontrado!')
    
    historico = await RepositorioCompetidor(db).get_historico_handicap(competidor_id)
    return success_response(historico)

# -------------------------- Validações --------------------------

@router.post("/competidor/validar-trio", tags=['Competidor Trio'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def validar_trio(
    dados: Dict[str, Any] = Body(..., example={
        "competidores_ids": [1, 2, 3],
        "categoria_id": 1
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Valida se um trio atende às regras da categoria"""
    
    competidores_ids = dados.get('competidores_ids', [])
    categoria_id = dados.get('categoria_id')
    
    if not competidores_ids or len(competidores_ids) != 3:
        return error_response(message='Deve informar exatamente 3 competidores!')
    
    if not categoria_id:
        return error_response(message='Categoria é obrigatória!')
    
    valido, mensagem = await RepositorioCompetidor(db).validar_trio_handicap(competidores_ids, categoria_id)
    
    return success_response({
        'valido': valido,
        'mensagem': mensagem,
        'competidores_ids': competidores_ids,
        'categoria_id': categoria_id
    })

@router.post("/competidor/validar-categoria", tags=['Competidor Categoria'], 
            status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def validar_categoria_competidor(
    dados: Dict[str, Any] = Body(..., example={
        "competidor_id": 1,
        "categoria_id": 1
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Valida se um competidor pode ser associado a uma categoria"""
    
    competidor_id = dados.get('competidor_id')
    categoria_id = dados.get('categoria_id')
    
    if not competidor_id or not categoria_id:
        return error_response(message='Deve informar competidor_id e categoria_id')
    
    repo = RepositorioCompetidor(db)
    valido, mensagem = await repo.validar_categoria_competidor(competidor_id, categoria_id)
    
    return success_response({
        'valido': valido,
        'mensagem': mensagem,
        'competidor_id': competidor_id,
        'categoria_id': categoria_id
    })

# -------------------------- Relatórios --------------------------

@router.get("/competidor/relatorio/participacao", tags=['Competidor Relatórios'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def relatorio_participacao(
    data_inicio: date = Query(..., description="Data de início do período"),
    data_fim: date = Query(..., description="Data de fim do período"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera relatório de participação por período"""
    
    if data_inicio > data_fim:
        return error_response(message='Data de início não pode ser maior que a data de fim!')
    
    relatorio = await RepositorioCompetidor(db).relatorio_participacao_por_periodo(data_inicio, data_fim)
    if not relatorio:
        return error_response(message='Nenhum dado encontrado para o período informado!')
    
    return success_response(relatorio)

# -------------------------- Operações em Lote --------------------------

@router.post("/competidor/criar-multiplos", tags=['Competidor Lote'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def criar_multiplos_competidores(
    competidores: List[models.CompetidorPOST] = Body(..., min_items=1),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria múltiplos competidores em uma operação"""
    
    try:
        competidores_criados = await RepositorioCompetidor(db).criar_multiplos(competidores)
        return success_response(
            competidores_criados, 
            f'{len(competidores_criados)} competidores criados com sucesso',
            status_code=201
        )
    except ValueError as e:
        return error_response(message=str(e))

@router.put("/competidor/atualizar-handicaps", tags=['Competidor Lote'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def atualizar_handicaps_lote(
    updates: List[Dict[str, Any]] = Body(..., example=[
        {"id": 1, "handicap": 3},
        {"id": 2, "handicap": 4}
    ]),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Atualiza handicaps de múltiplos competidores"""
    
    # Validar dados
    for update in updates:
        if 'id' not in update or 'handicap' not in update:
            return error_response(message='Cada item deve conter "id" e "handicap"!')
        
        if not isinstance(update['handicap'], int) or update['handicap'] < 0 or update['handicap'] > 7:
            return error_response(message='Handicap deve ser um número inteiro entre 0 e 7!')
    
    try:
        sucesso = await RepositorioCompetidor(db).atualizar_handicaps_em_lote(updates)
        if sucesso:
            return success_response(None, f'{len(updates)} handicaps atualizados com sucesso')
        else:
            return error_response(message='Erro ao atualizar handicaps!')
    except Exception as e:
        return error_response(message=str(e))

# -------------------------- Exportação --------------------------

@router.get("/competidor/exportar", tags=['Competidor Exportação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def exportar_competidor(
    formato: str = Query(default="json", pattern="^(json|csv)$", description="Formato de exportação"),
    nome: Optional[str] = Query(default=None),
    handicap: Optional[int] = Query(default=None),
    cidade: Optional[str] = Query(default=None),
    estado: Optional[str] = Query(default=None),
    sexo: Optional[str] = Query(default=None),
    categoria_id: Optional[int] = Query(default=None),
    categoria_tipo: Optional[str] = Query(default=None),
    ativo: Optional[bool] = Query(default=True),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Exporta dados de competidores em diferentes formatos"""
    
    try:
        # Aplicar filtros se fornecidos
        competidores = await RepositorioCompetidor(db).get_all(
            nome=nome,
            handicap=handicap,
            cidade=cidade,
            estado=estado,
            sexo=sexo,
            categoria_id=categoria_id,
            categoria_tipo=categoria_tipo,
            ativo=ativo
        )
        
        if not competidores:
            return error_response(message='Nenhum competidor encontrado para exportação!')
        
        if formato == "csv":
            # Converter para formato CSV-friendly
            dados_csv = []
            for comp in competidores:
                dados_csv.append({
                    'id': comp.id,
                    'nome': comp.nome,
                    'login': comp.login,
                    'data_nascimento': comp.data_nascimento.strftime('%d/%m/%Y'),
                    'idade': comp.idade,
                    'handicap': comp.handicap,
                    'categoria_id': comp.categoria_id or '',
                    'cidade': comp.cidade or '',
                    'estado': comp.estado or '',
                    'sexo': comp.sexo,
                    'ativo': 'Sim' if comp.ativo else 'Não',
                    'criado_em': comp.created_at.strftime('%d/%m/%Y %H:%M') if comp.created_at else ''
                })
            
            return success_response({
                'formato': 'csv',
                'total_registros': len(dados_csv),
                'dados': dados_csv
            })
        else:
            # Formato JSON padrão
            return success_response({
                'formato': 'json',
                'total_registros': len(competidores),
                'dados': competidores
            })
            
    except Exception as e:
        return error_response(message=f'Erro na exportação: {str(e)}')

# -------------------------- Importação --------------------------

@router.post("/competidor/importar", tags=['Competidor Importação'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def importar_competidores(
    dados: Dict[str, Any] = Body(..., example={
        "competidores": [
            {
                "nome": "João Silva",
                "login": "joao.silva",
                "data_nascimento": "1990-05-15",
                "handicap": 3,
                "cidade": "São Paulo",
                "estado": "SP",
                "sexo": "M",
                "categoria_id": 1
            }
        ],
        "validar_apenas": False
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Importa competidores a partir de dados fornecidos"""
    
    competidores_dados = dados.get('competidores', [])
    validar_apenas = dados.get('validar_apenas', False)
    
    if not competidores_dados:
        return error_response(message='Nenhum dado de competidor fornecido!')
    
    try:
        # Validar dados
        competidores_validados = []
        erros_validacao = []
        
        for i, comp_data in enumerate(competidores_dados):
            try:
                # Converter data se necessário
                if isinstance(comp_data.get('data_nascimento'), str):
                    from datetime import datetime
                    comp_data['data_nascimento'] = datetime.strptime(
                        comp_data['data_nascimento'], '%Y-%m-%d'
                    ).date()
                
                # Validar usando o modelo Pydantic
                competidor = models.CompetidorPOST(**comp_data)
                competidores_validados.append(competidor)
                
            except Exception as e:
                erros_validacao.append({
                    'linha': i + 1,
                    'erro': str(e),
                    'dados': comp_data
                })
        
        if erros_validacao:
            return error_response(
                message=f'{len(erros_validacao)} erros de validação encontrados!',
                data={'erros': erros_validacao}
            )
        
        if validar_apenas:
            return success_response({
                'validacao': 'OK',
                'total_validados': len(competidores_validados),
                'competidores': competidores_validados
            })
        
        # Criar competidores
        competidores_criados = await RepositorioCompetidor(db).criar_multiplos(competidores_validados)
        
        return success_response(
            {
                'total_importados': len(competidores_criados),
                'competidores': competidores_criados
            },
            f'{len(competidores_criados)} competidores importados com sucesso',
            status_code=201
        )
        
    except Exception as e:
        return error_response(message=f'Erro na importação: {str(e)}')

# -------------------------- Rotas de Apoio --------------------------

@router.get("/competidor/opcoes/estados", tags=['Competidor Apoio'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_estados_disponiveis(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista estados únicos cadastrados"""
    
    try:
        from sqlalchemy import distinct
        estados = db.query(distinct(schemas.Competidores.estado)).filter(
            schemas.Competidores.estado.isnot(None),
            schemas.Competidores.ativo == True
        ).all()
        
        estados_lista = [estado[0] for estado in estados if estado[0]]
        return success_response(sorted(estados_lista))
    except Exception as e:
        return error_response(message=f'Erro ao buscar estados: {str(e)}')

@router.get("/competidor/opcoes/cidades", tags=['Competidor Apoio'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_cidades_disponiveis(
    estado: Optional[str] = Query(default=None, max_length=2, description="Filtrar por estado"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista cidades únicas cadastradas"""
    
    try:
        from sqlalchemy import distinct
        query = db.query(distinct(schemas.Competidores.cidade)).filter(
            schemas.Competidores.cidade.isnot(None),
            schemas.Competidores.ativo == True
        )
        
        if estado:
            query = query.filter(schemas.Competidores.estado == estado)
        
        cidades = query.all()
        cidades_lista = [cidade[0] for cidade in cidades if cidade[0]]
        return success_response(sorted(cidades_lista))
    except Exception as e:
        return error_response(message=f'Erro ao buscar cidades: {str(e)}')

@router.get("/competidor/opcoes/categorias", tags=['Competidor Apoio'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_categorias_disponiveis(
    ativas_apenas: bool = Query(default=True, description="Apenas categorias ativas"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista categorias disponíveis para competidores"""
    
    try:
        from sqlalchemy import select
        
        query = select(schemas.Categorias)
        if ativas_apenas:
            query = query.where(schemas.Categorias.ativa == True)
        
        categorias = db.execute(query).scalars().all()
        
        categorias_lista = [
            {
                'id': cat.id,
                'nome': cat.nome,
                'tipo': cat.tipo,
                'descricao': cat.descricao,
                'ativa': cat.ativa
            }
            for cat in categorias
        ]
        
        return success_response(categorias_lista)
    except Exception as e:
        return error_response(message=f'Erro ao buscar categorias: {str(e)}')
    

@router.get("/competidor/controle-participacao/{competidor_id:int}", tags=['Competidor Controle'], 
           status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_controle_participacao(
    competidor_id: int = Path(..., description="ID do competidor"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista controles de participação de um competidor"""
    
    # Verificar se o competidor existe
    competidor = await RepositorioCompetidor(db).get_by_id(competidor_id)
    if not competidor:
        return error_response(message='Competidor não encontrado!')
    
    try:
        controles = db.execute(
            select(schemas.ControleParticipacao)
            .join(schemas.Provas)
            .join(schemas.Categorias)
            .where(schemas.ControleParticipacao.competidor_id == competidor_id)
            .order_by(schemas.ControleParticipacao.created_at.desc())
        ).scalars().all()
        
        controles_dados = []
        for controle in controles:
            prova = db.execute(select(schemas.Provas).where(schemas.Provas.id == controle.prova_id)).scalars().first()
            categoria = db.execute(select(schemas.Categorias).where(schemas.Categorias.id == controle.categoria_id)).scalars().first()
            
            controles_dados.append({
                'id': controle.id,
                'competidor_id': controle.competidor_id,
                'prova_id': controle.prova_id,
                'prova_nome': prova.nome if prova else 'Prova não encontrada',
                'prova_data': prova.data if prova else None,
                'categoria_id': controle.categoria_id,
                'categoria_nome': categoria.nome if categoria else 'Categoria não encontrada',
                'total_passadas_executadas': controle.total_passadas_executadas,
                'max_passadas_permitidas': controle.max_passadas_permitidas,
                'passadas_restantes': controle.passadas_restantes,
                'percentual_uso': controle.percentual_uso,
                'pode_competir': controle.pode_competir,
                'motivo_bloqueio': controle.motivo_bloqueio,
                'primeira_passada': controle.primeira_passada,
                'ultima_passada': controle.ultima_passada,
                'created_at': controle.created_at,
                'updated_at': controle.updated_at
            })
        
        return success_response(controles_dados)
    except Exception as e:
        return error_response(message=f'Erro ao buscar controles: {str(e)}')

@router.post("/competidor/controle-participacao", tags=['Competidor Controle'], 
            status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def criar_controle_participacao(
    dados: Dict[str, Any] = Body(..., example={
        "competidor_id": 1,
        "prova_id": 1,
        "categoria_id": 1,
        "max_passadas_permitidas": 6,
        "pode_competir": True,
        "motivo_bloqueio": None
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria controle de participação para um competidor"""
    
    competidor_id = dados.get('competidor_id')
    prova_id = dados.get('prova_id')
    categoria_id = dados.get('categoria_id')
    max_passadas = dados.get('max_passadas_permitidas', 6)
    pode_competir = dados.get('pode_competir', True)
    motivo_bloqueio = dados.get('motivo_bloqueio')
    
    if not all([competidor_id, prova_id, categoria_id]):
        return error_response(message='competidor_id, prova_id e categoria_id são obrigatórios')
    
    # Verificar se já existe
    controle_existente = db.execute(
        select(schemas.ControleParticipacao).where(
            schemas.ControleParticipacao.competidor_id == competidor_id,
            schemas.ControleParticipacao.prova_id == prova_id,
            schemas.ControleParticipacao.categoria_id == categoria_id
        )
    ).scalars().first()
    
    if controle_existente:
        return error_response(message='Controle já existe para este competidor/prova/categoria')
    
    try:
        # Validar se não pode competir deve ter motivo
        if not pode_competir and not motivo_bloqueio:
            motivo_bloqueio = "Bloqueado por administrador"
        
        controle = schemas.ControleParticipacao(
            competidor_id=competidor_id,
            prova_id=prova_id,
            categoria_id=categoria_id,
            max_passadas_permitidas=max_passadas,
            pode_competir=pode_competir,
            motivo_bloqueio=motivo_bloqueio
        )
        
        db.add(controle)
        db.commit()
        db.refresh(controle)
        
        return success_response({
            'id': controle.id,
            'competidor_id': controle.competidor_id,
            'prova_id': controle.prova_id,
            'categoria_id': controle.categoria_id,
            'max_passadas_permitidas': controle.max_passadas_permitidas,
            'pode_competir': controle.pode_competir,
            'motivo_bloqueio': controle.motivo_bloqueio
        }, 'Controle de participação criado com sucesso', status_code=201)
        
    except Exception as e:
        db.rollback()
        return error_response(message=f'Erro ao criar controle: {str(e)}')

@router.put("/competidor/controle-participacao/{controle_id:int}", tags=['Competidor Controle'], 
           status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def atualizar_controle_participacao(
    controle_id: int = Path(..., description="ID do controle"),
    dados: Dict[str, Any] = Body(..., example={
        "max_passadas_permitidas": 6,
        "pode_competir": False,
        "motivo_bloqueio": "Suspenso por comportamento inadequado"
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Atualiza controle de participação"""
    
    controle = db.execute(
        select(schemas.ControleParticipacao).where(schemas.ControleParticipacao.id == controle_id)
    ).scalars().first()
    
    if not controle:
        return error_response(message='Controle não encontrado!')
    
    try:
        # Atualizar campos permitidos
        if 'max_passadas_permitidas' in dados:
            controle.max_passadas_permitidas = dados['max_passadas_permitidas']
        
        if 'pode_competir' in dados:
            controle.pode_competir = dados['pode_competir']
        
        if 'motivo_bloqueio' in dados:
            controle.motivo_bloqueio = dados['motivo_bloqueio']
        
        # Validar se não pode competir deve ter motivo
        if not controle.pode_competir and not controle.motivo_bloqueio:
            controle.motivo_bloqueio = "Bloqueado por administrador"
        
        # Atualizar contadores
        controle.atualizar_contadores()
        
        db.commit()
        
        return success_response({
            'id': controle.id,
            'max_passadas_permitidas': controle.max_passadas_permitidas,
            'pode_competir': controle.pode_competir,
            'motivo_bloqueio': controle.motivo_bloqueio,
            'passadas_restantes': controle.passadas_restantes
        }, 'Controle atualizado com sucesso')
        
    except Exception as e:
        db.rollback()
        return error_response(message=f'Erro ao atualizar controle: {str(e)}')

@router.delete("/competidor/controle-participacao/{controle_id:int}", tags=['Competidor Controle'], 
              status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def excluir_controle_participacao(
    controle_id: int = Path(..., description="ID do controle"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Exclui controle de participação"""
    
    controle = db.execute(
        select(schemas.ControleParticipacao).where(schemas.ControleParticipacao.id == controle_id)
    ).scalars().first()
    
    if not controle:
        return error_response(message='Controle não encontrado!')
    
    try:
        # Verificar se tem passadas executadas
        if controle.total_passadas_executadas > 0:
            return error_response(message='Não é possível excluir controle com passadas já executadas!')
        
        db.delete(controle)
        db.commit()
        
        return success_response(None, 'Controle excluído com sucesso')
        
    except Exception as e:
        db.rollback()
        return error_response(message=f'Erro ao excluir controle: {str(e)}')

@router.get("/competidor/provas-disponiveis/{competidor_id:int}/{categoria_id:int}", tags=['Competidor Controle'], 
           status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_provas_disponiveis_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista provas onde o competidor ainda pode ser inscrito na categoria específica"""
    
    # Verificar se o competidor existe
    competidor = await RepositorioCompetidor(db).get_by_id(competidor_id)
    if not competidor:
        return error_response(message='Competidor não encontrado!')
    
    # Verificar se a categoria existe
    categoria = db.execute(
        select(schemas.Categorias).where(schemas.Categorias.id == categoria_id)
    ).scalars().first()
    if not categoria:
        return error_response(message='Categoria não encontrada!')
    
    try:
        # Buscar provas ativas (futuras)
        provas_ativas = db.execute(
            select(schemas.Provas).where(
                schemas.Provas.ativa == True,
                schemas.Provas.data >= date.today()  # Apenas provas futuras
            ).order_by(schemas.Provas.data)
        ).scalars().all()
        
        provas_disponiveis = []
        for prova in provas_ativas:
            # Verificar se já tem controle para esta prova/categoria específica
            controle_existente = db.execute(
                select(schemas.ControleParticipacao).where(
                    schemas.ControleParticipacao.competidor_id == competidor_id,
                    schemas.ControleParticipacao.prova_id == prova.id,
                    schemas.ControleParticipacao.categoria_id == categoria_id
                )
            ).scalars().first()
            
            if not controle_existente:
                provas_disponiveis.append({
                    'id': prova.id,
                    'nome': prova.nome,
                    'data': prova.data,
                    'cidade': prova.cidade,
                    'estado': prova.estado,
                    'rancho': prova.rancho,
                    'tipo_copa': prova.tipo_copa
                })
        
        return success_response(provas_disponiveis)
        
    except Exception as e:
        return error_response(message=f'Erro ao buscar provas disponíveis: {str(e)}')
    
@router.post("/competidor/auto-criar-participacao/{competidor_id:int}", tags=['Competidor Controle'], 
            status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def auto_criar_participacao_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Auto-cria controles de participação para competidor com categoria definida"""
    
    # Verificar se o competidor existe e tem categoria
    competidor = await RepositorioCompetidor(db).get_by_id(competidor_id)
    if not competidor:
        return error_response(message='Competidor não encontrado!')
    
    if not competidor.categoria_id:
        return error_response(message='Competidor deve ter categoria definida!')
    
    try:
        # Buscar provas ativas futuras
        provas_futuras = db.execute(
            select(schemas.Provas).where(
                schemas.Provas.ativa == True,
                schemas.Provas.data >= date.today()
            ).order_by(schemas.Provas.data)
        ).scalars().all()
        
        controles_criados = []
        
        for prova in provas_futuras:
            # Verificar se já existe controle
            controle_existente = db.execute(
                select(schemas.ControleParticipacao).where(
                    schemas.ControleParticipacao.competidor_id == competidor_id,
                    schemas.ControleParticipacao.prova_id == prova.id,
                    schemas.ControleParticipacao.categoria_id == competidor.categoria_id
                )
            ).scalars().first()
            
            if not controle_existente:
                # Buscar configuração de passadas para esta prova/categoria
                config_passadas = db.execute(
                    select(schemas.ConfiguracaoPassadasProva).where(
                        schemas.ConfiguracaoPassadasProva.prova_id == prova.id,
                        schemas.ConfiguracaoPassadasProva.categoria_id == competidor.categoria_id,
                        schemas.ConfiguracaoPassadasProva.ativa == True
                    )
                ).scalars().first()
                
                # Definir máximo de passadas baseado na configuração
                max_passadas = 6  # Padrão
                if config_passadas:
                    max_passadas = config_passadas.max_corridas_por_pessoa
                
                # Criar controle
                controle = schemas.ControleParticipacao(
                    competidor_id=competidor_id,
                    prova_id=prova.id,
                    categoria_id=competidor.categoria_id,
                    max_passadas_permitidas=max_passadas,
                    pode_competir=True,
                    motivo_bloqueio=None
                )
                
                db.add(controle)
                controles_criados.append({
                    'prova_id': prova.id,
                    'prova_nome': prova.nome,
                    'max_passadas_permitidas': max_passadas,
                    'fonte_configuracao': bool(config_passadas)
                })
        
        db.commit()
        
        return success_response({
            'competidor_id': competidor_id,
            'categoria_id': competidor.categoria_id,
            'total_controles_criados': len(controles_criados),
            'controles_criados': controles_criados
        }, f'{len(controles_criados)} controles de participação criados automaticamente')
        
    except Exception as e:
        db.rollback()
        return error_response(message=f'Erro ao criar controles automáticos: {str(e)}')

@router.get("/competidor/configuracao-passadas/{prova_id:int}/{categoria_id:int}", tags=['Competidor Controle'], 
           status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def obter_configuracao_passadas_prova(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém configuração de passadas para uma prova/categoria específica"""
    
    try:
        config_passadas = db.execute(
            select(schemas.ConfiguracaoPassadasProva).where(
                schemas.ConfiguracaoPassadasProva.prova_id == prova_id,
                schemas.ConfiguracaoPassadasProva.categoria_id == categoria_id,
                schemas.ConfiguracaoPassadasProva.ativa == True
            )
        ).scalars().first()
        
        if config_passadas:
            return success_response({
                'id': config_passadas.id,
                'prova_id': config_passadas.prova_id,
                'categoria_id': config_passadas.categoria_id,
                'max_passadas_por_trio': config_passadas.max_passadas_por_trio,
                'max_corridas_por_pessoa': config_passadas.max_corridas_por_pessoa,
                'tempo_limite_padrao': config_passadas.tempo_limite_padrao,
                'intervalo_minimo_passadas': config_passadas.intervalo_minimo_passadas,
                'permite_repetir_boi': config_passadas.permite_repetir_boi,
                'ativa': config_passadas.ativa
            })
        else:
            # Retornar configuração padrão
            return success_response({
                'configuracao_encontrada': False,
                'max_corridas_por_pessoa': 6,  # Padrão
                'max_passadas_por_trio': 1,
                'observacao': 'Configuração padrão - nenhuma configuração específica encontrada'
            })
            
    except Exception as e:
        return error_response(message=f'Erro ao buscar configuração: {str(e)}')
    
@router.post("/competidor/atualizar-participacao-massa", tags=['Competidor Controle'], 
            status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def atualizar_participacao_massa(
    dados: Dict[str, Any] = Body(..., example={
        "competidores_ids": [1, 2, 3, 4, 5],
        "prova_id": 1,
        "categoria_id": 1,
        "max_passadas_permitidas": 6,
        "pode_competir": True,
        "motivo_bloqueio": None,
        "sobrescrever_existentes": False
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Atualiza controle de participação em massa para múltiplos competidores"""
    
    competidores_ids = dados.get('competidores_ids', [])
    prova_id = dados.get('prova_id')
    categoria_id = dados.get('categoria_id')
    max_passadas = dados.get('max_passadas_permitidas', 6)
    pode_competir = dados.get('pode_competir', True)
    motivo_bloqueio = dados.get('motivo_bloqueio')
    sobrescrever = dados.get('sobrescrever_existentes', False)
    
    if not competidores_ids or not prova_id or not categoria_id:
        return error_response(message='competidores_ids, prova_id e categoria_id são obrigatórios')
    
    try:
        resultados = {
            'total_processados': 0,
            'controles_criados': 0,
            'controles_atualizados': 0,
            'erros': [],
            'detalhes': []
        }
        
        for competidor_id in competidores_ids:
            try:
                # Verificar se competidor existe
                competidor = await RepositorioCompetidor(db).get_by_id(competidor_id)
                if not competidor:
                    resultados['erros'].append(f'Competidor ID {competidor_id} não encontrado')
                    continue
                
                # Verificar se já existe controle
                controle_existente = db.execute(
                    select(schemas.ControleParticipacao).where(
                        schemas.ControleParticipacao.competidor_id == competidor_id,
                        schemas.ControleParticipacao.prova_id == prova_id,
                        schemas.ControleParticipacao.categoria_id == categoria_id
                    )
                ).scalars().first()
                
                if controle_existente:
                    if sobrescrever:
                        # Atualizar controle existente
                        controle_existente.max_passadas_permitidas = max_passadas
                        controle_existente.pode_competir = pode_competir
                        controle_existente.motivo_bloqueio = motivo_bloqueio if not pode_competir else None
                        controle_existente.atualizar_contadores()
                        
                        resultados['controles_atualizados'] += 1
                        resultados['detalhes'].append({
                            'competidor_id': competidor_id,
                            'competidor_nome': competidor.nome,
                            'acao': 'atualizado'
                        })
                    else:
                        resultados['erros'].append(f'Competidor {competidor.nome} já tem controle para esta prova/categoria')
                        continue
                else:
                    # Criar novo controle
                    if not pode_competir and not motivo_bloqueio:
                        motivo_bloqueio = "Bloqueado por administrador"
                    
                    controle = schemas.ControleParticipacao(
                        competidor_id=competidor_id,
                        prova_id=prova_id,
                        categoria_id=categoria_id,
                        max_passadas_permitidas=max_passadas,
                        pode_competir=pode_competir,
                        motivo_bloqueio=motivo_bloqueio
                    )
                    
                    db.add(controle)
                    resultados['controles_criados'] += 1
                    resultados['detalhes'].append({
                        'competidor_id': competidor_id,
                        'competidor_nome': competidor.nome,
                        'acao': 'criado'
                    })
                
                resultados['total_processados'] += 1
                
            except Exception as e:
                resultados['erros'].append(f'Erro no competidor ID {competidor_id}: {str(e)}')
        
        db.commit()
        
        # Mensagem de sucesso personalizada
        total_sucesso = resultados['controles_criados'] + resultados['controles_atualizados']
        mensagem = f'Processamento concluído: {total_sucesso} controles de participação processados com sucesso'
        
        if resultados['erros']:
            mensagem += f' - {len(resultados["erros"])} erros encontrados'
        
        return success_response(resultados, mensagem)
        
    except Exception as e:
        db.rollback()
        return error_response(message=f'Erro na atualização em massa: {str(e)}')
    
async def auto_criar_controles_participacao(competidor_id: int, categoria_id: int, db: Session):
    """Função auxiliar para auto-criar controles de participação"""
    
    # Buscar provas ativas futuras
    provas_futuras = db.execute(
        select(schemas.Provas).where(
            schemas.Provas.ativa == True,
            schemas.Provas.data >= date.today()
        )
    ).scalars().all()
    
    controles_criados = 0
    
    for prova in provas_futuras:
        # Verificar se já existe controle
        controle_existente = db.execute(
            select(schemas.ControleParticipacao).where(
                schemas.ControleParticipacao.competidor_id == competidor_id,
                schemas.ControleParticipacao.prova_id == prova.id,
                schemas.ControleParticipacao.categoria_id == categoria_id
            )
        ).scalars().first()
        
        if not controle_existente:
            # Buscar configuração
            config_passadas = db.execute(
                select(schemas.ConfiguracaoPassadasProva).where(
                    schemas.ConfiguracaoPassadasProva.prova_id == prova.id,
                    schemas.ConfiguracaoPassadasProva.categoria_id == categoria_id,
                    schemas.ConfiguracaoPassadasProva.ativa == True
                )
            ).scalars().first()
            
            max_passadas = config_passadas.max_corridas_por_pessoa if config_passadas else 3
            
            # Criar controle
            controle = schemas.ControleParticipacao(
                competidor_id=competidor_id,
                prova_id=prova.id,
                categoria_id=categoria_id,
                max_passadas_permitidas=max_passadas,
                pode_competir=True
            )
            
            db.add(controle)
            controles_criados += 1
    
    if controles_criados > 0:
        db.commit()
    
    return controles_criados