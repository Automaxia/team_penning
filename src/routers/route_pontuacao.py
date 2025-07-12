from fastapi import APIRouter, status, Depends, HTTPException, Path, Query, Body
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, date
from src.utils.auth_utils import obter_usuario_logado
from src.database.db import get_db
from src.database import models, schemas
from src.utils.api_response import success_response, error_response
from src.repositorios.pontuacao import RepositorioPontuacao
from src.utils.route_error_handler import RouteErrorHandler

router = APIRouter(route_class=RouteErrorHandler)

# -------------------------- Operações Básicas CRUD --------------------------

@router.get("/pontuacao/consultar/{pontuacao_id}", tags=['Pontuação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def consultar_pontuacao(
    pontuacao_id: int = Path(..., description="ID da pontuação"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Consulta uma pontuação específica pelo ID"""
    
    pontuacao = await RepositorioPontuacao(db).get_by_id(pontuacao_id)
    if not pontuacao:
        return error_response(message='Pontuação não encontrada!')
    
    return success_response(pontuacao)

@router.post("/pontuacao/criar", tags=['Pontuação'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def criar_pontuacao(
    pontuacao_data: models.PontuacaoPOST,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria uma nova pontuação manualmente"""
    
    try:
        pontuacao = await RepositorioPontuacao(db).post(pontuacao_data)
        return success_response(pontuacao, 'Pontuação criada com sucesso', status_code=201)
    except ValueError as e:
        return error_response(message=str(e))

@router.put("/pontuacao/atualizar/{pontuacao_id}", tags=['Pontuação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def atualizar_pontuacao(
    pontuacao_id: int = Path(..., description="ID da pontuação"),
    pontuacao_data: models.PontuacaoPUT = Body(...),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Atualiza uma pontuação existente"""
    
    try:
        pontuacao = await RepositorioPontuacao(db).put(pontuacao_id, pontuacao_data)
        if not pontuacao:
            return error_response(message='Pontuação não encontrada!')
        
        return success_response(pontuacao, 'Pontuação atualizada com sucesso')
    except ValueError as e:
        return error_response(message=str(e))

@router.delete("/pontuacao/deletar/{pontuacao_id}", tags=['Pontuação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def excluir_pontuacao(
    pontuacao_id: int = Path(..., description="ID da pontuação"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Remove uma pontuação"""
    
    try:
        sucesso = await RepositorioPontuacao(db).delete(pontuacao_id)
        if sucesso:
            return success_response(None, 'Pontuação removida com sucesso')
        else:
            return error_response(message='Erro ao remover pontuação')
    except ValueError as e:
        return error_response(message=str(e))

# -------------------------- Consultas por Competidor --------------------------

@router.get("/pontuacao/competidor/{competidor_id}", tags=['Pontuação Competidor'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def pontuacoes_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    categoria_id: Optional[int] = Query(default=None, description="Categoria específica (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista todas as pontuações de um competidor"""
    
    pontuacoes = await RepositorioPontuacao(db).get_by_competidor(competidor_id, ano, categoria_id)
    if not pontuacoes:
        return error_response(message='Nenhuma pontuação encontrada para este competidor!')
    
    return success_response(pontuacoes, f'{len(pontuacoes)} pontuações encontradas')

@router.get("/pontuacao/competidor/{competidor_id}/estatisticas", tags=['Pontuação Competidor'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def estatisticas_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera estatísticas detalhadas de um competidor"""
    
    estatisticas = await RepositorioPontuacao(db).get_estatisticas_competidor(competidor_id, ano)
    if not estatisticas or estatisticas.get('total_provas', 0) == 0:
        return error_response(message='Nenhum dado encontrado para este competidor!')
    
    return success_response(estatisticas)

@router.get("/pontuacao/competidor/{competidor_id}/historico-categoria/{categoria_id}", tags=['Pontuação Competidor'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def historico_competidor_categoria(
    competidor_id: int = Path(..., description="ID do competidor"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna histórico completo de um competidor em uma categoria"""
    
    historico = await RepositorioPontuacao(db).get_historico_competidor_categoria(competidor_id, categoria_id)
    if not historico or historico.get('estatisticas', {}).get('total_participacoes', 0) == 0:
        return error_response(message='Nenhum histórico encontrado para este competidor nesta categoria!')
    
    return success_response(historico)

# -------------------------- Consultas por Prova --------------------------

@router.get("/pontuacao/prova/{prova_id}", tags=['Pontuação Prova'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def pontuacoes_prova(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(default=None, description="Categoria específica (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista pontuações de uma prova"""
    
    pontuacoes = await RepositorioPontuacao(db).get_by_prova(prova_id, categoria_id)
    if not pontuacoes:
        return error_response(message='Nenhuma pontuação encontrada para esta prova!')
    
    return success_response(pontuacoes, f'{len(pontuacoes)} pontuações encontradas')

@router.post("/pontuacao/prova/{prova_id}/recalcular", tags=['Pontuação Prova'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def recalcular_pontuacao_prova(
    prova_id: int = Path(..., description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Recalcula toda a pontuação de uma prova baseada nos resultados"""
    
    try:
        resultado = await RepositorioPontuacao(db).recalcular_pontuacao_prova(prova_id)
        return success_response(resultado, 'Pontuação da prova recalculada com sucesso')
    except Exception as e:
        return error_response(message=f'Erro ao recalcular pontuação: {str(e)}')

# -------------------------- Consultas por Categoria --------------------------

@router.get("/pontuacao/categoria/{categoria_id}", tags=['Pontuação Categoria'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def pontuacoes_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    limite: Optional[int] = Query(default=30, description="Limite de resultados"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista pontuações de uma categoria"""
    
    pontuacoes = await RepositorioPontuacao(db).get_by_categoria(categoria_id, ano, limite)
    if not pontuacoes:
        return error_response(message='Nenhuma pontuação encontrada para esta categoria!')
    
    return success_response(pontuacoes, f'{len(pontuacoes)} pontuações encontradas')

@router.get("/pontuacao/categoria/{categoria_id}/media", tags=['Pontuação Categoria'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def media_pontos_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Calcula médias de pontuação de uma categoria"""
    
    medias = await RepositorioPontuacao(db).get_media_pontos_categoria(categoria_id, ano)
    if medias.get('sem_dados'):
        return error_response(message='Nenhum dado encontrado para esta categoria!')
    
    return success_response(medias)

# -------------------------- Rankings --------------------------

@router.get("/pontuacao/ranking/geral", tags=['Rankings'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def ranking_geral(
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    categoria_id: Optional[int] = Query(default=None, description="Categoria específica (opcional)"),
    limite: int = Query(default=50, description="Número de posições no ranking"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera ranking geral de competidores"""
    
    ranking = await RepositorioPontuacao(db).get_ranking_geral(ano, categoria_id, limite)
    if not ranking:
        return error_response(message='Nenhum dado encontrado para gerar ranking!')
    
    return success_response(ranking, f'Ranking com {len(ranking)} posições')

@router.get("/pontuacao/ranking/categoria/{categoria_id}", tags=['Rankings'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def ranking_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    limite: int = Query(default=30, description="Número de posições no ranking"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera ranking específico de uma categoria"""
    
    ranking = await RepositorioPontuacao(db).get_ranking_categoria(categoria_id, ano, limite)
    if not ranking:
        return error_response(message='Nenhum dado encontrado para esta categoria!')
    
    return success_response(ranking, f'Ranking da categoria com {len(ranking)} posições')

@router.get("/pontuacao/ranking/top-competidores", tags=['Rankings'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def top_competidores_pontos(
    categoria_id: Optional[int] = Query(default=None, description="Categoria específica (opcional)"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    limite: int = Query(default=10, description="Número de competidores"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna competidores com mais pontos no período"""
    
    top_competidores = await RepositorioPontuacao(db).get_competidores_com_mais_pontos(categoria_id, ano, limite)
    if not top_competidores:
        return error_response(message='Nenhum dado encontrado!')
    
    return success_response(top_competidores, f'Top {len(top_competidores)} competidores')

# -------------------------- Cálculos Automáticos --------------------------

@router.post("/pontuacao/calcular-resultado", tags=['Pontuação Cálculo'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def calcular_pontuacao_resultado(
    dados: Dict[str, Any] = Body(..., example={
        "resultado_id": 1
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Calcula pontuação baseada em um resultado específico"""
    
    resultado_id = dados.get('resultado_id')
    if not resultado_id:
        return error_response(message='Deve informar o ID do resultado')
    
    try:
        # Buscar resultado
        resultado = db.execute(
            schemas.select(schemas.Resultados).where(schemas.Resultados.id == resultado_id)
        ).scalars().first()
        
        if not resultado:
            return error_response(message='Resultado não encontrado!')
        
        calculo = await RepositorioPontuacao(db).calcular_pontuacao_resultado(resultado)
        return success_response(calculo, 'Pontuação calculada com sucesso', status_code=201)
    except Exception as e:
        return error_response(message=f'Erro no cálculo: {str(e)}')

@router.post("/pontuacao/recalcular/{pontuacao_id}", tags=['Pontuação Cálculo'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def recalcular_pontos(
    pontuacao_id: int = Path(..., description="ID da pontuação"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Recalcula todos os pontos de uma pontuação específica"""
    
    try:
        sucesso = await RepositorioPontuacao(db).recalcular_todos_pontos(pontuacao_id)
        if sucesso:
            return success_response(None, 'Pontos recalculados com sucesso')
        else:
            return error_response(message='Pontuação não encontrada ou erro no recálculo')
    except Exception as e:
        return error_response(message=f'Erro no recálculo: {str(e)}')

# -------------------------- Relatórios --------------------------

@router.get("/pontuacao/relatorio/ano/{ano}", tags=['Pontuação Relatórios'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def relatorio_pontuacao_ano(
    ano: int = Path(..., description="Ano do relatório"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera relatório completo de pontuação do ano"""
    
    try:
        relatorio = await RepositorioPontuacao(db).gerar_relatorio_pontuacao_ano(ano)
        if relatorio.get('total_pontuacoes', 0) == 0:
            return error_response(message=f'Nenhum dado de pontuação encontrado para o ano {ano}!')
        
        return success_response(relatorio, f'Relatório do ano {ano} gerado com sucesso')
    except Exception as e:
        return error_response(message=f'Erro ao gerar relatório: {str(e)}')

@router.get("/pontuacao/relatorio/resumo", tags=['Pontuação Relatórios'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def resumo_pontuacao_geral(
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna resumo geral do sistema de pontuação"""
    
    try:
        repo = RepositorioPontuacao(db)
        
        # Estatísticas básicas
        ranking_geral = await repo.get_ranking_geral(ano, None, 10)
        
        if not ranking_geral:
            return error_response(message='Nenhum dado de pontuação encontrado!')
        
        # Calcular totais
        total_competidores = len(ranking_geral)
        total_pontos = sum(c['total_pontos'] for c in ranking_geral)
        total_provas = sum(c['total_provas'] for c in ranking_geral)
        premiacao_total = sum(c['premiacao_total'] for c in ranking_geral)
        
        resumo = {
            'ano': ano or 'todos_os_anos',
            'total_competidores_ativos': total_competidores,
            'total_pontos_distribuidos': round(total_pontos, 2),
            'total_participacoes': total_provas,
            'premiacao_total_distribuida': round(premiacao_total, 2),
            'media_pontos_por_competidor': round(total_pontos / total_competidores, 2) if total_competidores > 0 else 0,
            'media_participacoes_por_competidor': round(total_provas / total_competidores, 2) if total_competidores > 0 else 0,
            'top_3_competidores': ranking_geral[:3],
            'gerado_em': datetime.now().isoformat()
        }
        
        return success_response(resumo)
    except Exception as e:
        return error_response(message=f'Erro ao gerar resumo: {str(e)}')

# -------------------------- Validações --------------------------

@router.post("/pontuacao/validar-consistencia", tags=['Pontuação Validação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def validar_consistencia_pontuacao(
    prova_id: Optional[int] = Query(default=None, description="ID da prova (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Valida consistência dos dados de pontuação"""
    
    try:
        validacao = await RepositorioPontuacao(db).validar_consistencia_pontuacao(prova_id)
        
        if validacao['valido']:
            return success_response(validacao, 'Dados de pontuação estão consistentes')
        else:
            return success_response(validacao, f'{validacao["total_inconsistencias"]} inconsistências encontradas')
    except Exception as e:
        return error_response(message=f'Erro na validação: {str(e)}')

@router.post("/pontuacao/validar-calculo", tags=['Pontuação Validação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def validar_calculo_pontos(
    dados: Dict[str, Any] = Body(..., example={
        "colocacao": 1,
        "premiacao_valor": 500.0
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Valida cálculo de pontos sem salvar"""
    
    try:
        from src.utils.utils_lctp import UtilsLCTP
        
        colocacao = dados.get('colocacao')
        premiacao_valor = dados.get('premiacao_valor', 0)
        
        pontos_colocacao = UtilsLCTP.calcular_pontos_colocacao(colocacao) if colocacao else 0
        pontos_premiacao = UtilsLCTP.calcular_pontos_premiacao(float(premiacao_valor)) if premiacao_valor else 0
        pontos_total = pontos_colocacao + pontos_premiacao
        
        resultado = {
            'entrada': {
                'colocacao': colocacao,
                'premiacao_valor': premiacao_valor
            },
            'calculo': {
                'pontos_colocacao': pontos_colocacao,
                'pontos_premiacao': pontos_premiacao,
                'pontos_total': pontos_total
            },
            'valido': True
        }
        
        return success_response(resultado, 'Cálculo de pontos validado')
    except Exception as e:
        return error_response(message=f'Erro no cálculo: {str(e)}')

# -------------------------- Exportação e Importação --------------------------

@router.get("/pontuacao/exportar", tags=['Pontuação Exportação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def exportar_pontuacoes(
    formato: str = Query(default="json", regex="^(json|csv)$", description="Formato de exportação"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    categoria_id: Optional[int] = Query(default=None, description="Categoria específica (opcional)"),
    competidor_id: Optional[int] = Query(default=None, description="Competidor específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Exporta pontuações com filtros opcionais"""
    
    try:
        filtros = {}
        if ano:
            filtros['ano'] = ano
        if categoria_id:
            filtros['categoria_id'] = categoria_id
        if competidor_id:
            filtros['competidor_id'] = competidor_id
        
        dados = await RepositorioPontuacao(db).exportar_pontuacoes(filtros)
        
        return success_response({
            'formato': formato,
            'filtros_aplicados': filtros,
            'total_pontuacoes': len(dados),
            'dados': dados,
            'exportado_em': datetime.now().isoformat()
        })
    except Exception as e:
        return error_response(message=f'Erro na exportação: {str(e)}')

@router.post("/pontuacao/importar", tags=['Pontuação Importação'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def importar_pontuacoes(
    pontuacoes_data: List[models.PontuacaoPOST] = Body(...),
    sobrescrever: bool = Query(default=False, description="Sobrescrever pontuações existentes"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Importa pontuações em lote"""
    
    try:
        repo = RepositorioPontuacao(db)
        pontuacoes_criadas = []
        pontuacoes_atualizadas = []
        erros = []
        
        for pontuacao_data in pontuacoes_data:
            try:
                # Verificar se já existe
                pontuacao_existente = await repo.get_by_competidor_prova(
                    pontuacao_data.competidor_id,
                    pontuacao_data.prova_id,
                    pontuacao_data.categoria_id
                )
                
                if pontuacao_existente and sobrescrever:
                    # Atualizar existente
                    pontuacao_put = models.PontuacaoPUT(
                        pontos_colocacao=pontuacao_data.pontos_colocacao,
                        pontos_premiacao=pontuacao_data.pontos_premiacao,
                        pontos_total=pontuacao_data.pontos_total,
                        colocacao=pontuacao_data.colocacao,
                        premiacao_valor=pontuacao_data.premiacao_valor
                    )
                    pontuacao_atualizada = await repo.put(pontuacao_existente.id, pontuacao_put)
                    pontuacoes_atualizadas.append(pontuacao_atualizada)
                elif not pontuacao_existente:
                    # Criar nova
                    pontuacao_criada = await repo.post(pontuacao_data)
                    pontuacoes_criadas.append(pontuacao_criada)
                else:
                    erros.append(f"Pontuação já existe para competidor {pontuacao_data.competidor_id}")
                    
            except Exception as e:
                erros.append(f"Erro ao processar pontuação: {str(e)}")
        
        return success_response({
            'pontuacoes_criadas': len(pontuacoes_criadas),
            'pontuacoes_atualizadas': len(pontuacoes_atualizadas),
            'erros': erros,
            'dados': {
                'criadas': pontuacoes_criadas,
                'atualizadas': pontuacoes_atualizadas
            }
        }, f'Importação concluída: {len(pontuacoes_criadas)} criadas, {len(pontuacoes_atualizadas)} atualizadas', status_code=201)
        
    except Exception as e:
        return error_response(message=f'Erro na importação: {str(e)}')

# -------------------------- Utilitários --------------------------

@router.get("/pontuacao/tabela-pontos", tags=['Pontuação Utilitários'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def tabela_pontos_contep(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna a tabela de pontos CONTEP"""
    
    tabela = {
        'sistema': 'CONTEP',
        'descricao': 'Tabela oficial de pontuação por colocação',
        'pontos_por_colocacao': {
            1: 10, 2: 9, 3: 8, 4: 7, 5: 6,
            6: 5, 7: 4, 8: 3, 9: 2, 10: 1
        },
        'pontos_premiacao': {
            'formula': 'valor_premiacao / 100',
            'exemplo': 'R$ 500,00 = 5 pontos'
        },
        'observacoes': [
            'Apenas as 10 primeiras colocações pontuam',
            'Premiação: cada R$ 100,00 equivale a 1 ponto',
            'Pontuação total = pontos_colocacao + pontos_premiacao'
        ]
    }
    
    return success_response(tabela, 'Tabela de pontos CONTEP')

@router.get("/pontuacao/simulador", tags=['Pontuação Utilitários'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def simulador_pontuacao(
    colocacao: Optional[int] = Query(default=None, description="Colocação para simular"),
    premiacao: Optional[float] = Query(default=None, description="Valor da premiação"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Simulador de pontuação baseado em colocação e premiação"""
    
    try:
        from src.utils.utils_lctp import UtilsLCTP
        
        pontos_colocacao = UtilsLCTP.calcular_pontos_colocacao(colocacao) if colocacao else 0
        pontos_premiacao = UtilsLCTP.calcular_pontos_premiacao(premiacao) if premiacao else 0
        pontos_total = pontos_colocacao + pontos_premiacao
        
        simulacao = {
            'entrada': {
                'colocacao': colocacao,
                'premiacao_valor': premiacao
            },
            'resultado': {
                'pontos_colocacao': pontos_colocacao,
                'pontos_premiacao': pontos_premiacao,
                'pontos_total': pontos_total
            },
            'detalhes': {
                'formula_colocacao': f'Posição {colocacao} = {pontos_colocacao} pontos' if colocacao else 'Sem colocação informada',
                'formula_premiacao': f'R$ {premiacao} ÷ 100 = {pontos_premiacao} pontos' if premiacao else 'Sem premiação informada',
                'observacao': 'Simulação baseada na tabela CONTEP'
            }
        }
        
        return success_response(simulacao, 'Simulação de pontuação calculada')
    except Exception as e:
        return error_response(message=f'Erro na simulação: {str(e)}')

# -------------------------- Busca Específica --------------------------

@router.get("/pontuacao/buscar", tags=['Pontuação Busca'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def buscar_pontuacoes(
    competidor_nome: Optional[str] = Query(default=None, description="Nome do competidor (busca parcial)"),
    prova_nome: Optional[str] = Query(default=None, description="Nome da prova (busca parcial)"),
    categoria_nome: Optional[str] = Query(default=None, description="Nome da categoria (busca parcial)"),
    ano_inicio: Optional[int] = Query(default=None, description="Ano inicial do período"),
    ano_fim: Optional[int] = Query(default=None, description="Ano final do período"),
    colocacao_min: Optional[int] = Query(default=None, description="Colocação mínima"),
    colocacao_max: Optional[int] = Query(default=None, description="Colocação máxima"),
    pontos_min: Optional[float] = Query(default=None, description="Pontos mínimos"),
    pontos_max: Optional[float] = Query(default=None, description="Pontos máximos"),
    limite: int = Query(default=100, description="Limite de resultados"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Busca pontuações com filtros avançados"""
    
    try:
        from sqlalchemy import and_, or_, extract
        
        # Query base
        stmt = db.query(schemas.Pontuacao).options(
            joinedload(schemas.Pontuacao.competidor),
            joinedload(schemas.Pontuacao.prova),
            joinedload(schemas.Pontuacao.categoria)
        )
        
        # Aplicar filtros
        filtros = []
        
        if competidor_nome:
            filtros.append(schemas.Competidores.nome.ilike(f"%{competidor_nome}%"))
            stmt = stmt.join(schemas.Competidores)
        
        if prova_nome:
            filtros.append(schemas.Provas.nome.ilike(f"%{prova_nome}%"))
            stmt = stmt.join(schemas.Provas)
        
        if categoria_nome:
            filtros.append(schemas.Categorias.nome.ilike(f"%{categoria_nome}%"))
            stmt = stmt.join(schemas.Categorias)
        
        if ano_inicio:
            if 'schemas.Provas' not in str(stmt):
                stmt = stmt.join(schemas.Provas)
            filtros.append(extract('year', schemas.Provas.data) >= ano_inicio)
        
        if ano_fim:
            if 'schemas.Provas' not in str(stmt):
                stmt = stmt.join(schemas.Provas)
            filtros.append(extract('year', schemas.Provas.data) <= ano_fim)
        
        if colocacao_min:
            filtros.append(schemas.Pontuacao.colocacao >= colocacao_min)
        
        if colocacao_max:
            filtros.append(schemas.Pontuacao.colocacao <= colocacao_max)
        
        if pontos_min:
            filtros.append(schemas.Pontuacao.pontos_total >= pontos_min)
        
        if pontos_max:
            filtros.append(schemas.Pontuacao.pontos_total <= pontos_max)
        
        if filtros:
            stmt = stmt.filter(and_(*filtros))
        
        # Ordenar e limitar
        stmt = stmt.order_by(desc(schemas.Pontuacao.pontos_total)).limit(limite)
        
        pontuacoes = stmt.all()
        
        if not pontuacoes:
            return error_response(message='Nenhuma pontuação encontrada com os filtros especificados!')
        
        # Preparar resposta com filtros aplicados
        filtros_aplicados = {
            'competidor_nome': competidor_nome,
            'prova_nome': prova_nome,
            'categoria_nome': categoria_nome,
            'periodo': f"{ano_inicio or 'início'} até {ano_fim or 'fim'}",
            'colocacao': f"{colocacao_min or 'mín'} até {colocacao_max or 'máx'}",
            'pontos': f"{pontos_min or 'mín'} até {pontos_max or 'máx'}"
        }
        
        return success_response({
            'pontuacoes': pontuacoes,
            'total_encontradas': len(pontuacoes),
            'filtros_aplicados': filtros_aplicados
        }, f'{len(pontuacoes)} pontuações encontradas')
        
    except Exception as e:
        return error_response(message=f'Erro na busca: {str(e)}')

@router.get("/pontuacao/buscar-duplicadas", tags=['Pontuação Busca'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def buscar_pontuacoes_duplicadas(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Busca pontuações duplicadas (mesmo competidor/prova/categoria)"""
    
    try:
        from sqlalchemy import func
        
        # Buscar registros duplicados
        duplicados = db.query(
            schemas.Pontuacao.competidor_id,
            schemas.Pontuacao.prova_id,
            schemas.Pontuacao.categoria_id,
            func.count(schemas.Pontuacao.id).label('total_registros')
        ).group_by(
            schemas.Pontuacao.competidor_id,
            schemas.Pontuacao.prova_id,
            schemas.Pontuacao.categoria_id
        ).having(
            func.count(schemas.Pontuacao.id) > 1
        ).all()
        
        if not duplicados:
            return success_response([], 'Nenhuma pontuação duplicada encontrada')
        
        # Buscar detalhes dos duplicados
        detalhes_duplicados = []
        for dup in duplicados:
            pontuacoes = db.query(schemas.Pontuacao).options(
                joinedload(schemas.Pontuacao.competidor),
                joinedload(schemas.Pontuacao.prova),
                joinedload(schemas.Pontuacao.categoria)
            ).filter(
                and_(
                    schemas.Pontuacao.competidor_id == dup.competidor_id,
                    schemas.Pontuacao.prova_id == dup.prova_id,
                    schemas.Pontuacao.categoria_id == dup.categoria_id
                )
            ).all()
            
            detalhes_duplicados.append({
                'competidor_id': dup.competidor_id,
                'prova_id': dup.prova_id,
                'categoria_id': dup.categoria_id,
                'total_registros': dup.total_registros,
                'competidor_nome': pontuacoes[0].competidor.nome if pontuacoes else 'N/A',
                'prova_nome': pontuacoes[0].prova.nome if pontuacoes else 'N/A',
                'categoria_nome': pontuacoes[0].categoria.nome if pontuacoes else 'N/A',
                'registros': [{
                    'id': p.id,
                    'pontos_total': p.pontos_total,
                    'colocacao': p.colocacao,
                    'created_at': p.created_at.isoformat() if p.created_at else None
                } for p in pontuacoes]
            })
        
        return success_response({
            'total_grupos_duplicados': len(detalhes_duplicados),
            'duplicados': detalhes_duplicados
        }, f'{len(detalhes_duplicados)} grupos de pontuações duplicadas encontrados')
        
    except Exception as e:
        return error_response(message=f'Erro ao buscar duplicados: {str(e)}')

# -------------------------- Análises Avançadas --------------------------

@router.get("/pontuacao/analise/evolucao-competidor/{competidor_id}", tags=['Pontuação Análises'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def analise_evolucao_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    categoria_id: Optional[int] = Query(default=None, description="Categoria específica (opcional)"),
    limite_provas: int = Query(default=20, description="Últimas N provas para análise"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Análise de evolução de desempenho de um competidor"""
    
    try:
        pontuacoes = await RepositorioPontuacao(db).get_by_competidor(competidor_id, None, categoria_id)
        
        if not pontuacoes:
            return error_response(message='Nenhuma pontuação encontrada para este competidor!')
        
        # Ordenar por data da prova (mais recentes primeiro)
        pontuacoes_ordenadas = sorted(pontuacoes, key=lambda p: p.prova.data, reverse=True)[:limite_provas]
        
        # Calcular métricas de evolução
        pontos_historico = [p.pontos_total for p in pontuacoes_ordenadas]
        colocacoes_historico = [p.colocacao for p in pontuacoes_ordenadas if p.colocacao]
        
        # Análise de tendência (últimas vs primeiras participações)
        meio = len(pontos_historico) // 2
        if meio > 0:
            media_recente = sum(pontos_historico[:meio]) / meio
            media_antiga = sum(pontos_historico[meio:]) / (len(pontos_historico) - meio)
            tendencia = "melhoria" if media_recente > media_antiga else "declínio" if media_recente < media_antiga else "estável"
            percentual_mudanca = ((media_recente - media_antiga) / media_antiga * 100) if media_antiga > 0 else 0
        else:
            media_recente = media_antiga = tendencia = percentual_mudanca = None
        
        # Sequências e recordes
        melhor_sequencia = 0
        sequencia_atual = 0
        for i in range(len(colocacoes_historico) - 1):
            if colocacoes_historico[i] <= colocacoes_historico[i + 1]:
                sequencia_atual += 1
                melhor_sequencia = max(melhor_sequencia, sequencia_atual)
            else:
                sequencia_atual = 0
        
        analise = {
            'competidor_id': competidor_id,
            'categoria_id': categoria_id,
            'periodo_analisado': {
                'total_provas': len(pontuacoes_ordenadas),
                'data_primeira': pontuacoes_ordenadas[-1].prova.data.isoformat() if pontuacoes_ordenadas else None,
                'data_ultima': pontuacoes_ordenadas[0].prova.data.isoformat() if pontuacoes_ordenadas else None
            },
            'metricas_gerais': {
                'media_pontos': round(sum(pontos_historico) / len(pontos_historico), 2) if pontos_historico else 0,
                'melhor_pontuacao': max(pontos_historico) if pontos_historico else 0,
                'pior_pontuacao': min(pontos_historico) if pontos_historico else 0,
                'melhor_colocacao': min(colocacoes_historico) if colocacoes_historico else None,
                'pior_colocacao': max(colocacoes_historico) if colocacoes_historico else None
            },
            'analise_tendencia': {
                'tendencia': tendencia,
                'percentual_mudanca': round(percentual_mudanca, 2) if percentual_mudanca else 0,
                'media_periodo_recente': round(media_recente, 2) if media_recente else 0,
                'media_periodo_anterior': round(media_antiga, 2) if media_antiga else 0
            },
            'consistencia': {
                'melhor_sequencia_melhoria': melhor_sequencia,
                'desvio_padrao_pontos': round(_calcular_desvio_padrao(pontos_historico), 2) if len(pontos_historico) > 1 else 0,
                'coeficiente_variacao': round(_calcular_desvio_padrao(pontos_historico) / (sum(pontos_historico) / len(pontos_historico)) * 100, 2) if pontos_historico and sum(pontos_historico) > 0 else 0
            },
            'historico_detalhado': [{
                'prova_nome': p.prova.nome,
                'prova_data': p.prova.data.isoformat(),
                'categoria': p.categoria.nome,
                'pontos': p.pontos_total,
                'colocacao': p.colocacao,
                'premiacao': float(p.premiacao_valor or 0)
            } for p in pontuacoes_ordenadas]
        }
        
        return success_response(analise, 'Análise de evolução gerada com sucesso')
        
    except Exception as e:
        return error_response(message=f'Erro na análise: {str(e)}')

@router.get("/pontuacao/analise/comparacao", tags=['Pontuação Análises'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def analise_comparacao_competidores(
    competidores_ids: str = Query(..., description="IDs dos competidores separados por vírgula (máx 5)"),
    categoria_id: Optional[int] = Query(default=None, description="Categoria específica (opcional)"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Análise comparativa entre competidores"""
    
    try:
        # Processar IDs
        ids_lista = [int(id.strip()) for id in competidores_ids.split(',') if id.strip().isdigit()]
        
        if len(ids_lista) < 2:
            return error_response(message='Informe pelo menos 2 competidores para comparação!')
        
        if len(ids_lista) > 5:
            return error_response(message='Máximo de 5 competidores para comparação!')
        
        repo = RepositorioPontuacao(db)
        comparacao = []
        
        for competidor_id in ids_lista:
            estatisticas = await repo.get_estatisticas_competidor(competidor_id, ano)
            if categoria_id and categoria_id in estatisticas.get('por_categoria', {}):
                stats_categoria = estatisticas['por_categoria'][categoria_id]
                estatisticas.update(stats_categoria)
            
            comparacao.append({
                'competidor_id': competidor_id,
                'competidor_nome': estatisticas.get('competidor_nome', 'N/A'),
                'total_provas': estatisticas.get('total_provas', 0),
                'total_pontos': estatisticas.get('total_pontos', 0),
                'media_pontos': estatisticas.get('media_pontos', 0),
                'melhor_colocacao': estatisticas.get('melhor_colocacao'),
                'premiacao_total': estatisticas.get('premiacao_total', 0)
            })
        
        # Ordenar por total de pontos
        comparacao.sort(key=lambda x: x['total_pontos'], reverse=True)
        
        # Adicionar posições na comparação
        for i, comp in enumerate(comparacao, 1):
            comp['posicao_comparacao'] = i
        
        # Estatísticas da comparação
        pontos_todos = [c['total_pontos'] for c in comparacao]
        provas_todos = [c['total_provas'] for c in comparacao]
        
        resultado = {
            'parametros': {
                'competidores_comparados': len(comparacao),
                'categoria_id': categoria_id,
                'ano': ano
            },
            'resultados': comparacao,
            'estatisticas_grupo': {
                'maior_pontuacao': max(pontos_todos) if pontos_todos else 0,
                'menor_pontuacao': min(pontos_todos) if pontos_todos else 0,
                'media_pontuacao_grupo': round(sum(pontos_todos) / len(pontos_todos), 2) if pontos_todos else 0,
                'total_provas_grupo': sum(provas_todos),
                'media_provas_por_competidor': round(sum(provas_todos) / len(provas_todos), 2) if provas_todos else 0
            }
        }
        
        return success_response(resultado, 'Comparação entre competidores gerada com sucesso')
        
    except Exception as e:
        return error_response(message=f'Erro na comparação: {str(e)}')

@router.get("/pontuacao/analise/categoria-performance/{categoria_id}", tags=['Pontuação Análises'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def analise_performance_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Análise de performance geral de uma categoria"""
    
    try:
        repo = RepositorioPontuacao(db)
        
        # Dados básicos da categoria
        pontuacoes = await repo.get_by_categoria(categoria_id, ano)
        medias = await repo.get_media_pontos_categoria(categoria_id, ano)
        
        if not pontuacoes:
            return error_response(message='Nenhum dado encontrado para esta categoria!')
        
        # Análise de distribuição de pontos
        pontos_lista = [p.pontos_total for p in pontuacoes]
        colocacoes_lista = [p.colocacao for p in pontuacoes if p.colocacao]
        premiacoes_lista = [float(p.premiacao_valor or 0) for p in pontuacoes if p.premiacao_valor]
        
        # Distribuição por faixas de pontos
        faixas_pontos = {
            '0-2': len([p for p in pontos_lista if 0 <= p < 2]),
            '2-4': len([p for p in pontos_lista if 2 <= p < 4]),
            '4-6': len([p for p in pontos_lista if 4 <= p < 6]),
            '6-8': len([p for p in pontos_lista if 6 <= p < 8]),
            '8-10': len([p for p in pontos_lista if 8 <= p < 10]),
            '10+': len([p for p in pontos_lista if p >= 10])
        }
        
        # Distribuição por colocações
        faixas_colocacao = {
            '1º-3º': len([c for c in colocacoes_lista if 1 <= c <= 3]),
            '4º-6º': len([c for c in colocacoes_lista if 4 <= c <= 6]),
            '7º-10º': len([c for c in colocacoes_lista if 7 <= c <= 10]),
            '11º+': len([c for c in colocacoes_lista if c > 10])
        }
        
        # Top performers
        ranking = await repo.get_ranking_categoria(categoria_id, ano, 10)
        
        analise = {
            'categoria_id': categoria_id,
            'ano': ano,
            'estatisticas_gerais': medias,
            'distribuicao_pontos': faixas_pontos,
            'distribuicao_colocacoes': faixas_colocacao,
            'metricas_performance': {
                'pontuacao_maxima': max(pontos_lista) if pontos_lista else 0,
                'pontuacao_minima': min(pontos_lista) if pontos_lista else 0,
                'mediana_pontos': _calcular_mediana(pontos_lista),
                'desvio_padrao_pontos': round(_calcular_desvio_padrao(pontos_lista), 2) if len(pontos_lista) > 1 else 0,
                'total_premiacao_distribuida': round(sum(premiacoes_lista), 2) if premiacoes_lista else 0,
                'media_premiacao': round(sum(premiacoes_lista) / len(premiacoes_lista), 2) if premiacoes_lista else 0,
                'percentual_premiados': round(len(premiacoes_lista) / len(pontuacoes) * 100, 2) if pontuacoes else 0
            },
            'top_performers': ranking[:10],
            'competitividade': {
                'nivel': _avaliar_competitividade(pontos_lista),
                'concentracao_top3': sum(c['total_pontos'] for c in ranking[:3]) / sum(c['total_pontos'] for c in ranking) * 100 if len(ranking) >= 3 else 0
            }
        }
        
        return success_response(analise, 'Análise de performance da categoria gerada com sucesso')
        
    except Exception as e:
        return error_response(message=f'Erro na análise: {str(e)}')

# -------------------------- Funções Auxiliares --------------------------

def _calcular_desvio_padrao(valores: List[float]) -> float:
    """Calcula o desvio padrão de uma lista de valores"""
    if len(valores) < 2:
        return 0
    
    media = sum(valores) / len(valores)
    variancia = sum((x - media) ** 2 for x in valores) / (len(valores) - 1)
    return variancia ** 0.5

def _calcular_mediana(valores: List[float]) -> float:
    """Calcula a mediana de uma lista de valores"""
    if not valores:
        return 0
    
    valores_ordenados = sorted(valores)
    n = len(valores_ordenados)
    
    if n % 2 == 0:
        return (valores_ordenados[n//2 - 1] + valores_ordenados[n//2]) / 2
    else:
        return valores_ordenados[n//2]

def _avaliar_competitividade(pontos_lista: List[float]) -> str:
    """Avalia o nível de competitividade baseado na distribuição de pontos"""
    if not pontos_lista:
        return "indeterminado"
    
    desvio = _calcular_desvio_padrao(pontos_lista)
    media = sum(pontos_lista) / len(pontos_lista)
    coeficiente_variacao = (desvio / media * 100) if media > 0 else 0
    
    if coeficiente_variacao < 20:
        return "baixa"
    elif coeficiente_variacao < 40:
        return "média"
    elif coeficiente_variacao < 60:
        return "alta"
    else:
        return "muito alta"