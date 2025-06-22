from fastapi import APIRouter, status, Depends, HTTPException, Path, Query, Body
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, date
from src.utils.auth_utils import obter_usuario_logado
from src.database.db import get_db
from src.database import models_lctp
from src.utils.api_response import success_response, error_response
from src.repositorios.trio import RepositorioTrio
from src.repositorios.competidor import RepositorioCompetidor
from src.utils.route_error_handler import RouteErrorHandler

router = APIRouter(route_class=RouteErrorHandler)

# -------------------------- Rotas Básicas de Trios --------------------------

@router.get("/trio/consultar/{trio_id}", tags=['Trio'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def consultar_trio(
    trio_id: int = Path(..., description="ID do trio"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Consulta um trio específico com integrantes e resultados"""
    
    trio = await RepositorioTrio(db).get_by_id(trio_id)
    if not trio:
        return error_response(message='Trio não encontrado!')
    
    return success_response(trio)

@router.post("/trio/criar", tags=['Trio'], status_code=status.HTTP_201_CREATED, response_model=models_lctp.ApiResponse)
async def criar_trio(
    dados: models_lctp.TrioComIntegrantes,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria um trio com seus integrantes"""
    
    try:
        # Validar se pode criar o trio
        valido, mensagem = await RepositorioTrio(db).validar_inscricao_trio(
            dados.trio.prova_id,
            dados.trio.categoria_id,
            dados.integrantes
        )
        
        if not valido:
            return error_response(message=mensagem)
        
        trio = await RepositorioTrio(db).post(dados.trio, dados.integrantes)
        return success_response(trio, 'Trio criado com sucesso', status_code=201)
        
    except ValueError as e:
        return error_response(message=str(e))

@router.put("/trio/atualizar/{trio_id}", tags=['Trio'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def atualizar_trio(
    trio_id: int = Path(..., description="ID do trio"),
    trio_data: models_lctp.TrioPUT = Body(...),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Atualiza dados de um trio"""
    
    # Verificar se o trio existe
    trio_existente = await RepositorioTrio(db).get_by_id(trio_id)
    if not trio_existente:
        return error_response(message='Trio não encontrado!')
    
    try:
        trio_atualizado = await RepositorioTrio(db).put(trio_id, trio_data)
        return success_response(trio_atualizado, 'Trio atualizado com sucesso')
    except ValueError as e:
        return error_response(message=str(e))

@router.delete("/trio/deletar/{trio_id}", tags=['Trio'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def excluir_trio(
    trio_id: int = Path(..., description="ID do trio"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Remove um trio e seus integrantes"""
    
    # Verificar se o trio existe
    trio = await RepositorioTrio(db).get_by_id(trio_id)
    if not trio:
        return error_response(message='Trio não encontrado!')
    
    try:
        await RepositorioTrio(db).delete(trio_id)
        return success_response(None, 'Trio excluído com sucesso')
    except ValueError as e:
        return error_response(message=str(e))

# -------------------------- Consultas por Prova/Categoria --------------------------

@router.get("/trio/prova/{prova_id}", tags=['Trio Consulta'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def listar_trios_prova(
    prova_id: int = Path(..., description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista todos os trios de uma prova"""
    
    trios = await RepositorioTrio(db).get_trios_prova(prova_id)
    if not trios:
        return error_response(message='Nenhum trio encontrado para esta prova!')
    
    return success_response(trios)

@router.get("/trio/prova/{prova_id}/categoria/{categoria_id}", tags=['Trio Consulta'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def listar_trios_prova_categoria(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista trios de uma prova e categoria específicas"""
    
    trios = await RepositorioTrio(db).get_by_prova_categoria(prova_id, categoria_id)
    if not trios:
        return error_response(message='Nenhum trio encontrado para esta prova/categoria!')
    
    return success_response(trios)

# -------------------------- Sorteios --------------------------

@router.post("/trio/sortear", tags=['Trio Sorteio'], status_code=status.HTTP_201_CREATED, response_model=models_lctp.ApiResponse)
async def sortear_trios(
    dados: models_lctp.SorteioRequest,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Realiza sorteio de trios baseado nas regras da categoria"""
    
    try:
        resultado = await RepositorioTrio(db).sortear_trios(
            dados.prova_id,
            dados.categoria_id,
            dados.competidores_ids
        )
        
        return success_response(
            resultado,
            resultado['mensagem'],
            status_code=201
        )
        
    except ValueError as e:
        return error_response(message=str(e))

@router.post("/trio/validar-sorteio", tags=['Trio Sorteio'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def validar_sorteio(
    dados: Dict[str, Any] = Body(..., example={
        "prova_id": 1,
        "categoria_id": 1,
        "competidores_ids": [1, 2, 3, 4, 5, 6]
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Valida se é possível realizar sorteio com os competidores informados"""
    
    prova_id = dados.get('prova_id')
    categoria_id = dados.get('categoria_id')
    competidores_ids = dados.get('competidores_ids', [])
    
    if not prova_id or not categoria_id or not competidores_ids:
        return error_response(message='Dados obrigatórios: prova_id, categoria_id e competidores_ids')
    
    try:
        # Verificar categoria
        categoria = await db.execute(
            select(schemas_lctp.Categorias).where(schemas_lctp.Categorias.id == categoria_id)
        ).scalars().first()
        
        if not categoria:
            return error_response(message='Categoria não encontrada!')
        
        if not categoria.permite_sorteio:
            return error_response(message='Esta categoria não permite sorteio!')
        
        # Calcular quantos trios podem ser formados
        total_competidores = len(competidores_ids)
        max_trios = total_competidores // 3
        competidores_restantes = total_competidores % 3
        
        # Validações específicas por tipo
        validacao = {
            'valido': True,
            'total_competidores': total_competidores,
            'max_trios_possiveis': max_trios,
            'competidores_restantes': competidores_restantes,
            'categoria_tipo': categoria.tipo.value,
            'permite_sorteio': categoria.permite_sorteio,
            'observacoes': []
        }
        
        if categoria.tipo.value in ['kids', 'feminina']:
            min_sorteio = categoria.min_inscricoes_sorteio or 3
            max_sorteio = categoria.max_inscricoes_sorteio or 9
            
            if total_competidores < min_sorteio:
                validacao['valido'] = False
                validacao['observacoes'].append(f'Mínimo de {min_sorteio} competidores necessários para sorteio')
            
            if total_competidores > max_sorteio:
                validacao['observacoes'].append(f'Máximo de {max_sorteio} competidores serão sorteados')
        
        elif categoria.tipo.value == 'mirim':
            if categoria.idade_max_trio:
                validacao['observacoes'].append(f'Será respeitado limite de {categoria.idade_max_trio} anos por trio')
        
        if categoria.handicap_max_trio:
            validacao['observacoes'].append(f'Será respeitado limite de handicap {categoria.handicap_max_trio} por trio')
        
        return success_response(validacao)
        
    except Exception as e:
        return error_response(message=f'Erro na validação: {str(e)}')

# -------------------------- Copa dos Campeões --------------------------

@router.post("/trio/copa-campeoes", tags=['Trio Copa'], status_code=status.HTTP_201_CREATED, response_model=models_lctp.ApiResponse)
async def criar_trios_copa_campeoes(
    dados: Dict[str, Any] = Body(..., example={
        "prova_id": 1,
        "categoria_id": 1,
        "campeoes_handicap": [
            {"handicap": 0, "competidor_id": 1},
            {"handicap": 1, "competidor_id": 2},
            {"handicap": 2, "competidor_id": 3}
        ]
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria trios para Copa dos Campeões com cabeças de chave"""
    
    prova_id = dados.get('prova_id')
    categoria_id = dados.get('categoria_id')
    campeoes_handicap = dados.get('campeoes_handicap', [])
    
    if not prova_id or not categoria_id or not campeoes_handicap:
        return error_response(message='Dados obrigatórios: prova_id, categoria_id e campeoes_handicap')
    
    try:
        resultado = await RepositorioTrio(db).criar_trios_copa_campeoes(
            prova_id, categoria_id, campeoes_handicap
        )
        
        return success_response(
            resultado,
            resultado['mensagem'],
            status_code=201
        )
        
    except ValueError as e:
        return error_response(message=str(e))

@router.get("/trio/campeoes-elegiveis", tags=['Trio Copa'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def listar_campeoes_elegiveis(
    ano: Optional[int] = Query(default=None, description="Ano para buscar campeões"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista campeões elegíveis para Copa dos Campeões por handicap"""
    
    try:
        campeoes = await RepositorioCompetidor(db).get_campeoes_por_handicap(ano)
        if not campeoes:
            return error_response(message='Nenhum campeão encontrado!')
        
        # Organizar por handicap
        campeoes_organizados = {}
        for campeao in campeoes:
            handicap = campeao.handicap
            if handicap not in campeoes_organizados:
                campeoes_organizados[handicap] = []
            campeoes_organizados[handicap].append(campeao)
        
        return success_response({
            'ano': ano or 'todos',
            'campeoes_por_handicap': campeoes_organizados,
            'total_campeoes': len(campeoes)
        })
        
    except Exception as e:
        return error_response(message=f'Erro ao buscar campeões: {str(e)}')

# -------------------------- Estatísticas e Ranking --------------------------

@router.get("/trio/estatisticas/{trio_id}", tags=['Trio Estatísticas'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def estatisticas_trio(
    trio_id: int = Path(..., description="ID do trio"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Recupera estatísticas completas de um trio"""
    
    estatisticas = await RepositorioTrio(db).get_estatisticas_trio(trio_id)
    if not estatisticas:
        return error_response(message='Trio não encontrado ou sem dados!')
    
    return success_response(estatisticas)

@router.get("/trio/ranking/categoria/{categoria_id}", tags=['Trio Ranking'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def ranking_trios_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera ranking de trios por categoria"""
    
    ranking = await RepositorioTrio(db).get_ranking_trios_categoria(categoria_id, ano)
    if not ranking:
        return error_response(message='Nenhum dado encontrado para gerar o ranking!')
    
    return success_response(ranking)

# -------------------------- Validações --------------------------

@router.post("/trio/validar-inscricao", tags=['Trio Validação'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def validar_inscricao_trio(
    dados: Dict[str, Any] = Body(..., example={
        "prova_id": 1,
        "categoria_id": 1,
        "competidores_ids": [1, 2, 3]
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Valida se um trio pode ser inscrito em uma prova/categoria"""
    
    prova_id = dados.get('prova_id')
    categoria_id = dados.get('categoria_id')
    competidores_ids = dados.get('competidores_ids', [])
    
    if not prova_id or not categoria_id or len(competidores_ids) != 3:
        return error_response(message='Deve informar prova_id, categoria_id e exatamente 3 competidores!')
    
    valido, mensagem = await RepositorioTrio(db).validar_inscricao_trio(
        prova_id, categoria_id, competidores_ids
    )
    
    return success_response({
        'valido': valido,
        'mensagem': mensagem,
        'prova_id': prova_id,
        'categoria_id': categoria_id,
        'competidores_ids': competidores_ids
    })

# -------------------------- Operações em Lote --------------------------

@router.post("/trio/criar-multiplos", tags=['Trio Lote'], status_code=status.HTTP_201_CREATED, response_model=models_lctp.ApiResponse)
async def criar_multiplos_trios(
    trios_data: List[Dict[str, Any]] = Body(..., example=[
        {
            "trio": {
                "prova_id": 1,
                "categoria_id": 1,
                "numero_trio": 1,
                "formacao_manual": True
            },
            "competidores_ids": [1, 2, 3]
        }
    ]),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria múltiplos trios em uma operação"""
    
    try:
        trios_criados = await RepositorioTrio(db).criar_multiplos_trios(trios_data)
        return success_response(
            trios_criados,
            f'{len(trios_criados)} trios criados com sucesso',
            status_code=201
        )
    except ValueError as e:
        return error_response(message=str(e))

@router.put("/trio/reorganizar-numeros/{prova_id}/{categoria_id}", tags=['Trio Lote'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def reorganizar_numeros_trio(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Reorganiza a numeração dos trios de uma prova/categoria"""
    
    try:
        sucesso = await RepositorioTrio(db).atualizar_numeros_trio(prova_id, categoria_id)
        if sucesso:
            return success_response(None, 'Numeração dos trios reorganizada com sucesso')
        else:
            return error_response(message='Erro ao reorganizar numeração!')
    except Exception as e:
        return error_response(message=str(e))

# -------------------------- Relatórios --------------------------

@router.get("/trio/relatorio/participacao-prova/{prova_id}", tags=['Trio Relatórios'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def relatorio_participacao_prova(
    prova_id: int = Path(..., description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera relatório de participação em uma prova"""
    
    try:
        trios = await RepositorioTrio(db).get_trios_prova(prova_id)
        if not trios:
            return error_response(message='Nenhum trio encontrado para esta prova!')
        
        # Agrupar por categoria
        relatorio_categorias = {}
        total_competidores = 0
        
        for trio in trios:
            categoria_nome = trio.categoria.nome
            if categoria_nome not in relatorio_categorias:
                relatorio_categorias[categoria_nome] = {
                    'categoria_id': trio.categoria_id,
                    'trios': [],
                    'total_trios': 0,
                    'total_competidores': 0
                }
            
            relatorio_categorias[categoria_nome]['trios'].append(trio)
            relatorio_categorias[categoria_nome]['total_trios'] += 1
            relatorio_categorias[categoria_nome]['total_competidores'] += len(trio.integrantes)
            total_competidores += len(trio.integrantes)
        
        relatorio = {
            'prova_id': prova_id,
            'total_trios': len(trios),
            'total_competidores': total_competidores,
            'categorias': relatorio_categorias
        }
        
        return success_response(relatorio)
        
    except Exception as e:
        return error_response(message=f'Erro ao gerar relatório: {str(e)}')

@router.get("/trio/relatorio/formacao-tipos", tags=['Trio Relatórios'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def relatorio_tipos_formacao(
    prova_id: Optional[int] = Query(default=None, description="ID da prova (opcional)"),
    categoria_id: Optional[int] = Query(default=None, description="ID da categoria (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera relatório dos tipos de formação de trios"""
    
    try:
        query = db.query(schemas_lctp.Trios)
        
        if prova_id:
            query = query.filter(schemas_lctp.Trios.prova_id == prova_id)
        if categoria_id:
            query = query.filter(schemas_lctp.Trios.categoria_id == categoria_id)
        
        trios = query.all()
        
        if not trios:
            return error_response(message='Nenhum trio encontrado!')
        
        # Estatísticas de formação
        estatisticas = {
            'total_trios': len(trios),
            'formacao_manual': len([t for t in trios if t.formacao_manual]),
            'formacao_sorteio': len([t for t in trios if not t.formacao_manual]),
            'cabecas_chave': len([t for t in trios if t.is_cabeca_chave]),
            'copa_campeoes': len([t for t in trios if t.cup_type and t.cup_type.value == 'copa_campeoes']),
            'por_status': {}
        }
        
        # Agrupar por status
        for trio in trios:
            status = trio.status.value if trio.status else 'indefinido'
            if status not in estatisticas['por_status']:
                estatisticas['por_status'][status] = 0
            estatisticas['por_status'][status] += 1
        
        return success_response(estatisticas)
        
    except Exception as e:
        return error_response(message=f'Erro ao gerar relatório: {str(e)}')

# -------------------------- Exportação --------------------------

@router.get("/trio/exportar", tags=['Trio Exportação'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def exportar_trios(
    formato: str = Query(default="json", regex="^(json|csv)$", description="Formato de exportação"),
    prova_id: Optional[int] = Query(default=None, description="ID da prova"),
    categoria_id: Optional[int] = Query(default=None, description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Exporta dados de trios em diferentes formatos"""
    
    try:
        if prova_id and categoria_id:
            trios = await RepositorioTrio(db).get_by_prova_categoria(prova_id, categoria_id)
        elif prova_id:
            trios = await RepositorioTrio(db).get_trios_prova(prova_id)
        else:
            return error_response(message='Deve informar pelo menos prova_id')
        
        if not trios:
            return error_response(message='Nenhum trio encontrado para exportação!')
        
        if formato == "csv":
            # Converter para formato CSV-friendly
            dados_csv = []
            for trio in trios:
                # Dados do trio
                trio_base = {
                    'trio_id': trio.id,
                    'numero_trio': trio.numero_trio,
                    'prova_id': trio.prova_id,
                    'categoria_id': trio.categoria_id,
                    'categoria_nome': trio.categoria.nome,
                    'handicap_total': trio.handicap_total,
                    'idade_total': trio.idade_total,
                    'status': trio.status.value if trio.status else '',
                    'formacao_manual': 'Sim' if trio.formacao_manual else 'Não',
                    'cabeca_chave': 'Sim' if trio.is_cabeca_chave else 'Não'
                }
                
                # Adicionar dados dos integrantes
                for i, integrante in enumerate(trio.integrantes, 1):
                    comp = integrante.competidor
                    trio_linha = trio_base.copy()
                    trio_linha.update({
                        f'competidor_{i}_id': comp.id,
                        f'competidor_{i}_nome': comp.nome,
                        f'competidor_{i}_handicap': comp.handicap,
                        f'competidor_{i}_idade': comp.idade,
                        f'competidor_{i}_cidade': comp.cidade or '',
                        f'competidor_{i}_estado': comp.estado or ''
                    })
                    dados_csv.append(trio_linha)
            
            return success_response({
                'formato': 'csv',
                'total_registros': len(dados_csv),
                'dados': dados_csv
            })
        else:
            # Formato JSON padrão
            return success_response({
                'formato': 'json',
                'total_registros': len(trios),
                'dados': trios
            })
            
    except Exception as e:
        return error_response(message=f'Erro na exportação: {str(e)}')

# -------------------------- Utilitários --------------------------

@router.get("/trio/verificar-disponibilidade", tags=['Trio Utilitários'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def verificar_disponibilidade_competidores(
    prova_id: int = Query(..., description="ID da prova"),
    categoria_id: int = Query(..., description="ID da categoria"),
    competidores_ids: List[int] = Query(..., description="IDs dos competidores"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Verifica disponibilidade de competidores para uma prova/categoria"""
    
    try:
        disponibilidade = {}
        
        for comp_id in competidores_ids:
            # Verificar se já está inscrito
            inscricao = await db.execute(
                select(schemas_lctp.IntegrantesTrios).join(
                    schemas_lctp.Trios
                ).where(
                    schemas_lctp.Trios.prova_id == prova_id,
                    schemas_lctp.Trios.categoria_id == categoria_id,
                    schemas_lctp.IntegrantesTrios.competidor_id == comp_id
                )
            ).scalars().first()
            
            disponibilidade[comp_id] = {
                'disponivel': inscricao is None,
                'inscrito_trio_id': inscricao.trio_id if inscricao else None
            }
        
        return success_response(disponibilidade)
        
    except Exception as e:
        return error_response(message=f'Erro ao verificar disponibilidade: {str(e)}')

@router.get("/trio/sugestoes-completar", tags=['Trio Utilitários'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def sugestoes_completar_trio(
    prova_id: int = Query(..., description="ID da prova"),
    categoria_id: int = Query(..., description="ID da categoria"),
    competidores_base: List[int] = Query(..., description="Competidores já selecionados (1 ou 2)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Sugere competidores para completar um trio"""
    
    if len(competidores_base) == 0 or len(competidores_base) >= 3:
        return error_response(message='Deve informar 1 ou 2 competidores base!')
    
    try:
        # Buscar competidores disponíveis
        repo_competidor = RepositorioCompetidor(db)
        disponiveis = await repo_competidor.buscar_disponiveis_para_prova(prova_id, categoria_id)
        
        # Filtrar os já selecionados
        candidatos = [c for c in disponiveis if c.id not in competidores_base]
        
        sugestoes = []
        faltam = 3 - len(competidores_base)
        
        if faltam == 1:
            # Precisamos de apenas 1 competidor
            for candidato in candidatos:
                trio_teste = competidores_base + [candidato.id]
                valido, _ = await repo_competidor.validar_trio_handicap(trio_teste, categoria_id)
                
                if valido:
                    sugestoes.append({
                        'competidores_sugeridos': [candidato],
                        'trio_completo': trio_teste
                    })
        
        elif faltam == 2:
            # Precisamos de 2 competidores
            for i, comp1 in enumerate(candidatos):
                for comp2 in candidatos[i+1:]:
                    trio_teste = competidores_base + [comp1.id, comp2.id]
                    valido, _ = await repo_competidor.validar_trio_handicap(trio_teste, categoria_id)
                    
                    if valido:
                        sugestoes.append({
                            'competidores_sugeridos': [comp1, comp2],
                            'trio_completo': trio_teste
                        })
        
        # Limitar a 20 sugestões
        sugestoes = sugestoes[:20]
        
        return success_response({
            'competidores_base': competidores_base,
            'faltam': faltam,
            'total_sugestoes': len(sugestoes),
            'sugestoes': sugestoes
        })
        
    except Exception as e:
        return error_response(message=f'Erro ao gerar sugestões: {str(e)}')