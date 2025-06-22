# route_competidor.py
from fastapi import APIRouter, status, Depends, HTTPException, Path, Query, Body
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, date
from src.utils.auth_utils import obter_usuario_logado
from src.database.db import get_db
from src.database import models_lctp
from src.utils.api_response import success_response, error_response
from src.repositorios.competidor import RepositorioCompetidor
from src.utils.route_error_handler import RouteErrorHandler

router = APIRouter(route_class=RouteErrorHandler)

# -------------------------- Rotas Básicas de Competidores --------------------------

@router.get("/competidor/pesquisar", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def pesquisar_competidores(
    nome: Optional[str] = Query(default=None, max_length=300, description="Nome do competidor"),
    handicap: Optional[int] = Query(default=None, ge=0, le=7, description="Handicap do competidor"),
    cidade: Optional[str] = Query(default=None, max_length=100, description="Cidade do competidor"),
    estado: Optional[str] = Query(default=None, max_length=2, description="Estado (UF) do competidor"),
    sexo: Optional[str] = Query(default=None, regex="^[MF]$", description="Sexo do competidor (M/F)"),
    idade_min: Optional[int] = Query(default=None, ge=0, le=100, description="Idade mínima"),
    idade_max: Optional[int] = Query(default=None, ge=0, le=100, description="Idade máxima"),
    ativo: Optional[bool] = Query(default=True, description="Status ativo do competidor"),
    pagina: Optional[int] = Query(default=0, ge=0, description="Número da página"),
    tamanho_pagina: Optional[int] = Query(default=0, ge=0, description="Tamanho da página"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Pesquisa competidores com filtros diversos"""
    
    competidores = await RepositorioCompetidor(db).get_all(
        nome=nome,
        handicap=handicap, 
        cidade=cidade,
        estado=estado,
        sexo=sexo,
        idade_min=idade_min,
        idade_max=idade_max,
        ativo=ativo,
        pagina=pagina,
        tamanho_pagina=tamanho_pagina
    )
    
    if not competidores:
        return error_response(message='Nenhum competidor encontrado com os filtros informados!')
    
    return success_response(competidores)

@router.post("/competidor/salvar", tags=['Competidor'], status_code=status.HTTP_201_CREATED, response_model=models_lctp.ApiResponse)
async def criar_competidor(
    competidor: models_lctp.CompetidorPOST,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria um novo competidor"""
    
    try:
        novo_competidor = await RepositorioCompetidor(db).post(competidor)
        return success_response(novo_competidor, 'Competidor criado com sucesso', status_code=201)
    except ValueError as e:
        return error_response(message=str(e))

@router.put("/competidor/atualizar/{competidor_id}", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def atualizar_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    competidor: models_lctp.CompetidorPUT = Body(...),
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
        return success_response(competidor_atualizado, 'Competidor atualizado com sucesso')
    except ValueError as e:
        return error_response(message=str(e))

@router.get("/competidor/consultar/{competidor_id}", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
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

@router.delete("/competidor/deletar/{competidor_id}", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
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

# -------------------------- Consultas Específicas --------------------------

@router.get("/competidor/por-handicap/{handicap}", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
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

@router.get("/competidor/femininos", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def listar_femininos(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista competidores do sexo feminino"""
    
    competidores = await RepositorioCompetidor(db).get_femininos()
    if not competidores:
        return error_response(message='Nenhuma competidora encontrada!')
    
    return success_response(competidores)

@router.get("/competidor/por-faixa-etaria", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
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

@router.get("/competidor/elegivel-categoria/{categoria_id}", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def listar_elegiveis_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    excluir_ids: Optional[List[int]] = Query(default=None, description="IDs de competidores a excluir"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista competidores elegíveis para uma categoria específica"""
    
    competidores = await RepositorioCompetidor(db).buscar_para_trio(categoria_id, excluir_ids or [])
    if not competidores:
        return error_response(message='Nenhum competidor elegível encontrado para esta categoria!')
    
    return success_response(competidores)

@router.get("/competidor/disponiveis-prova/{prova_id}/{categoria_id}", tags=['Competidor'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def listar_disponiveis_prova(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista competidores disponíveis para uma prova (não inscritos ainda)"""
    
    competidores = await RepositorioCompetidor(db).buscar_disponiveis_para_prova(prova_id, categoria_id)
    if not competidores:
        return error_response(message='Nenhum competidor disponível para esta prova/categoria!')
    
    return success_response(competidores)

# -------------------------- Ranking e Estatísticas --------------------------

@router.get("/competidor/ranking/categoria/{categoria_id}", tags=['Competidor Ranking'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
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

@router.get("/competidor/estatisticas/{competidor_id}", tags=['Competidor Ranking'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
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

@router.get("/competidor/campeoes-handicap", tags=['Competidor Ranking'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
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

@router.get("/competidor/performance/{competidor_id}", tags=['Competidor Ranking'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
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

@router.get("/competidor/sugestoes-trio/{competidor_id}/{categoria_id}", tags=['Competidor Trio'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
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

# -------------------------- Validações --------------------------

@router.post("/competidor/validar-trio", tags=['Competidor Trio'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
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

# -------------------------- Relatórios --------------------------

@router.get("/competidor/relatorio/participacao", tags=['Competidor Relatórios'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
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

@router.get("/competidor/historico-handicap/{competidor_id}", tags=['Competidor Relatórios'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
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

# -------------------------- Operações em Lote --------------------------

@router.post("/competidor/criar-multiplos", tags=['Competidor Lote'], status_code=status.HTTP_201_CREATED, response_model=models_lctp.ApiResponse)
async def criar_multiplos_competidores(
    competidores: List[models_lctp.CompetidorPOST] = Body(..., min_items=1),
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

@router.put("/competidor/atualizar-handicaps", tags=['Competidor Lote'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
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

# -------------------------- Estatísticas Gerais --------------------------

@router.get("/competidor/estatisticas/geral", tags=['Competidor Estatísticas'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def estatisticas_gerais(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Recupera estatísticas gerais do sistema"""
    
    try:
        # Total de competidores ativos
        total_ativos = len(await RepositorioCompetidor(db).get_all(ativo=True))
        
        # Distribuição por handicap
        distribuicao_handicap = {}
        for h in range(8):  # 0 a 7
            competidores_h = await RepositorioCompetidor(db).get_by_handicap(h)
            distribuicao_handicap[f'handicap_{h}'] = len(competidores_h)
        
        # Distribuição por sexo
        femininos = await RepositorioCompetidor(db).get_femininos()
        masculinos = await RepositorioCompetidor(db).get_all(sexo='M', ativo=True)
        
        # Estatísticas por faixa etária
        faixas_etarias = {
            'baby': len(await RepositorioCompetidor(db).get_by_categoria_idade(0, 12)),
            'kids': len(await RepositorioCompetidor(db).get_by_categoria_idade(13, 17)),
            'adulto': len(await RepositorioCompetidor(db).get_by_categoria_idade(18, 100))
        }
        
        estatisticas = {
            'total_competidores': total_ativos,
            'distribuicao_handicap': distribuicao_handicap,
            'distribuicao_sexo': {
                'feminino': len(femininos),
                'masculino': len(masculinos)
            },
            'distribuicao_faixa_etaria': faixas_etarias
        }
        
        return success_response(estatisticas)
    except Exception as e:
        return error_response(message=f'Erro ao calcular estatísticas: {str(e)}')

# -------------------------- Exportação --------------------------

@router.get("/competidor/exportar", tags=['Competidor Exportação'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def exportar_competidores(
    formato: str = Query(default="json", regex="^(json|csv)$", description="Formato de exportação"),
    filtros: Optional[Dict[str, Any]] = Query(default=None, description="Filtros para exportação"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Exporta dados de competidores em diferentes formatos"""
    
    try:
        # Aplicar filtros se fornecidos
        competidores = await RepositorioCompetidor(db).get_all(
            nome=filtros.get('nome') if filtros else None,
            handicap=filtros.get('handicap') if filtros else None,
            cidade=filtros.get('cidade') if filtros else None,
            estado=filtros.get('estado') if filtros else None,
            sexo=filtros.get('sexo') if filtros else None,
            ativo=filtros.get('ativo', True) if filtros else True
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
                    'data_nascimento': comp.data_nascimento.strftime('%d/%m/%Y'),
                    'idade': comp.idade,
                    'handicap': comp.handicap,
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

@router.post("/competidor/importar", tags=['Competidor Importação'], status_code=status.HTTP_201_CREATED, response_model=models_lctp.ApiResponse)
async def importar_competidores(
    dados: Dict[str, Any] = Body(..., example={
        "competidores": [
            {
                "nome": "João Silva",
                "data_nascimento": "1990-05-15",
                "handicap": 3,
                "cidade": "São Paulo",
                "estado": "SP",
                "sexo": "M"
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
                competidor = models_lctp.CompetidorPOST(**comp_data)
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

@router.get("/competidor/opcoes/estados", tags=['Competidor Apoio'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def listar_estados_disponiveis(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista estados únicos cadastrados"""
    
    try:
        from sqlalchemy import distinct
        estados = db.query(distinct(schemas_lctp.Competidores.estado)).filter(
            schemas_lctp.Competidores.estado.isnot(None),
            schemas_lctp.Competidores.ativo == True
        ).all()
        
        estados_lista = [estado[0] for estado in estados if estado[0]]
        return success_response(sorted(estados_lista))
    except Exception as e:
        return error_response(message=f'Erro ao buscar estados: {str(e)}')

@router.get("/competidor/opcoes/cidades", tags=['Competidor Apoio'], status_code=status.HTTP_200_OK, response_model=models_lctp.ApiResponse)
async def listar_cidades_disponiveis(
    estado: Optional[str] = Query(default=None, max_length=2, description="Filtrar por estado"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista cidades únicas cadastradas"""
    
    try:
        from sqlalchemy import distinct
        query = db.query(distinct(schemas_lctp.Competidores.cidade)).filter(
            schemas_lctp.Competidores.cidade.isnot(None),
            schemas_lctp.Competidores.ativo == True
        )
        
        if estado:
            query = query.filter(schemas_lctp.Competidores.estado == estado)
        
        cidades = query.all()
        cidades_lista = [cidade[0] for cidade in cidades if cidade[0]]
        return success_response(sorted(cidades_lista))
    except Exception as e:
        return error_response(message=f'Erro ao buscar cidades: {str(e)}')