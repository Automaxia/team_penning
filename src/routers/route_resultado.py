from fastapi import APIRouter, status, Depends, HTTPException, Path, Query, Body
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, date
from src.utils.auth_utils import obter_usuario_logado
from src.database.db import get_db
from src.database import models, schemas
from src.utils.api_response import success_response, error_response
from src.repositorios.resultado import RepositorioResultado
from src.utils.route_error_handler import RouteErrorHandler

router = APIRouter(route_class=RouteErrorHandler)

# -------------------------- Operações Básicas CRUD --------------------------

@router.get("/resultado/consultar/{resultado_id}", tags=['Resultado'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def consultar_resultado(
    resultado_id: int = Path(..., description="ID do resultado"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Consulta um resultado específico pelo ID"""
    
    resultado = await RepositorioResultado(db).get_by_id(resultado_id)
    if not resultado:
        return error_response(message='Resultado não encontrado!')
    
    return success_response(resultado)

@router.get("/resultado/trio/{trio_id}", tags=['Resultado'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def consultar_resultado_trio(
    trio_id: int = Path(..., description="ID do trio"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Consulta resultado de um trio específico"""
    
    resultado = await RepositorioResultado(db).get_by_trio(trio_id)
    if not resultado:
        return error_response(message='Resultado não encontrado para este trio!')
    
    return success_response(resultado)

@router.post("/resultado/criar", tags=['Resultado'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def criar_resultado(
    resultado_data: models.ResultadoPOST,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria um novo resultado"""
    
    try:
        resultado = await RepositorioResultado(db).post(resultado_data)
        return success_response(resultado, 'Resultado criado com sucesso', status_code=201)
    except ValueError as e:
        return error_response(message=str(e))

@router.put("/resultado/atualizar/{resultado_id}", tags=['Resultado'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def atualizar_resultado(
    resultado_id: int = Path(..., description="ID do resultado"),
    resultado_data: models.ResultadoPUT = Body(...),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Atualiza um resultado existente"""
    
    try:
        resultado = await RepositorioResultado(db).put(resultado_id, resultado_data)
        if not resultado:
            return error_response(message='Resultado não encontrado!')
        
        return success_response(resultado, 'Resultado atualizado com sucesso')
    except ValueError as e:
        return error_response(message=str(e))

@router.delete("/resultado/deletar/{resultado_id}", tags=['Resultado'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def excluir_resultado(
    resultado_id: int = Path(..., description="ID do resultado"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Remove um resultado"""
    
    try:
        sucesso = await RepositorioResultado(db).delete(resultado_id)
        if sucesso:
            return success_response(None, 'Resultado removido com sucesso')
        else:
            return error_response(message='Erro ao remover resultado')
    except ValueError as e:
        return error_response(message=str(e))

# -------------------------- Consultas por Prova/Categoria --------------------------

@router.get("/resultado/prova/{prova_id}", tags=['Resultado Consulta'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_resultados_prova(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(default=None, description="ID da categoria (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista resultados de uma prova (opcionalmente filtrados por categoria)"""
    
    resultados = await RepositorioResultado(db).get_by_prova(prova_id, categoria_id)
    if not resultados:
        return error_response(message='Nenhum resultado encontrado para esta prova!')
    
    return success_response(resultados, f'{len(resultados)} resultados encontrados')

@router.get("/resultado/ranking/prova/{prova_id}/categoria/{categoria_id}", tags=['Resultado Ranking'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def ranking_prova_categoria(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera ranking detalhado de uma prova/categoria"""
    
    try:
        ranking = await RepositorioResultado(db).get_ranking_prova_categoria(prova_id, categoria_id)
        if not ranking:
            return error_response(message='Nenhum resultado encontrado para gerar ranking!')
        
        return success_response(ranking, f'Ranking gerado com {len(ranking)} posições')
    except Exception as e:
        return error_response(message=f'Erro ao gerar ranking: {str(e)}')

# -------------------------- Lançamento em Lote --------------------------

@router.post("/resultado/lancar-lote", tags=['Resultado Lote'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def lancar_resultados_lote(
    prova_id: int = Query(..., description="ID da prova"),
    resultados_data: List[Dict[str, Any]] = Body(..., example=[
        {
            "trio_id": 1,
            "passada1_tempo": 45.2,
            "passada2_tempo": 44.8,
            "colocacao": 1,
            "premiacao_valor": 500.0,
            "no_time": False,
            "desclassificado": False,
            "observacoes": "Excelente performance"
        }
    ]),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lança resultados de uma prova completa em lote"""
    
    try:
        resultado_operacao = await RepositorioResultado(db).lancar_resultados_prova(prova_id, resultados_data)
        
        if resultado_operacao['sucesso']:
            return success_response(
                resultado_operacao,
                f"Resultados processados: {resultado_operacao['resultados_criados']} criados, {resultado_operacao['resultados_atualizados']} atualizados",
                status_code=201
            )
        else:
            return error_response(
                message=f"Erros no processamento: {len(resultado_operacao['erros'])} erros encontrados",
                data=resultado_operacao
            )
    except Exception as e:
        return error_response(message=f'Erro no lançamento em lote: {str(e)}')

@router.post("/resultado/calcular-colocacoes", tags=['Resultado Lote'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def calcular_colocacoes_automaticas(
    prova_id: int = Query(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(default=None, description="ID da categoria (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Calcula colocações automaticamente baseado nos tempos médios"""
    
    try:
        sucesso = await RepositorioResultado(db).calcular_colocacoes_automaticas(prova_id, categoria_id)
        
        if sucesso:
            return success_response(None, 'Colocações calculadas automaticamente com sucesso')
        else:
            return error_response(message='Erro ao calcular colocações automaticamente')
    except Exception as e:
        return error_response(message=f'Erro no cálculo de colocações: {str(e)}')

# -------------------------- Pontuação CONTEP --------------------------

@router.post("/resultado/calcular-pontuacao", tags=['Resultado Pontuação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def calcular_pontuacao_contep(
    prova_id: int = Query(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(default=None, description="ID da categoria (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Calcula pontuação CONTEP para uma prova/categoria"""
    
    try:
        resultado_calculo = await RepositorioResultado(db).calcular_pontuacao_contep(prova_id, categoria_id)
        
        return success_response(
            resultado_calculo,
            f"Pontuação CONTEP calculada: {resultado_calculo['total_processado']} registros processados"
        )
    except Exception as e:
        return error_response(message=f'Erro no cálculo de pontuação: {str(e)}')

# -------------------------- Estatísticas e Relatórios --------------------------

@router.get("/resultado/estatisticas/categoria/{categoria_id}", tags=['Resultado Estatísticas'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def estatisticas_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera estatísticas de resultados por categoria"""
    
    try:
        estatisticas = await RepositorioResultado(db).get_estatisticas_resultado_categoria(categoria_id, ano)
        
        if not estatisticas:
            return error_response(message='Categoria não encontrada ou sem dados!')
        
        return success_response(estatisticas)
    except Exception as e:
        return error_response(message=f'Erro ao gerar estatísticas: {str(e)}')

@router.get("/resultado/melhores-tempos/categoria/{categoria_id}", tags=['Resultado Estatísticas'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def melhores_tempos_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    limite: int = Query(default=10, ge=1, le=50, description="Número de resultados"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna os melhores tempos de uma categoria"""
    
    try:
        melhores_tempos = await RepositorioResultado(db).get_melhores_tempos_categoria(categoria_id, limite, ano)
        
        if not melhores_tempos:
            return error_response(message='Nenhum tempo encontrado para esta categoria!')
        
        return success_response(melhores_tempos, f'Top {len(melhores_tempos)} melhores tempos')
    except Exception as e:
        return error_response(message=f'Erro ao buscar melhores tempos: {str(e)}')

@router.get("/resultado/relatorio/performance/{prova_id}", tags=['Resultado Relatórios'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def relatorio_performance_prova(
    prova_id: int = Path(..., description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera relatório completo de performance de uma prova"""
    
    try:
        relatorio = await RepositorioResultado(db).gerar_relatorio_performance_prova(prova_id)
        return success_response(relatorio)
    except Exception as e:
        return error_response(message=f'Erro ao gerar relatório: {str(e)}')

@router.get("/resultado/comparar/categorias/{prova_id}", tags=['Resultado Relatórios'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def comparar_performance_categorias(
    prova_id: int = Path(..., description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Compara performance entre categorias de uma prova"""
    
    try:
        comparacao = await RepositorioResultado(db).comparar_performance_categorias(prova_id)
        return success_response(comparacao)
    except Exception as e:
        return error_response(message=f'Erro na comparação: {str(e)}')

# -------------------------- Exportação e Importação --------------------------

@router.get("/resultado/exportar", tags=['Resultado Exportação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def exportar_resultados(
    prova_id: int = Query(..., description="ID da prova"),
    formato: str = Query(default="json", regex="^(json|csv)$", description="Formato de exportação"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Exporta resultados de uma prova em formato estruturado"""
    
    try:
        dados_exportacao = await RepositorioResultado(db).exportar_resultados_prova(prova_id, formato)
        return success_response(dados_exportacao)
    except Exception as e:
        return error_response(message=f'Erro na exportação: {str(e)}')

@router.post("/resultado/importar-csv", tags=['Resultado Importação'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def importar_resultados_csv(
    prova_id: int = Query(..., description="ID da prova"),
    dados_csv: List[Dict[str, Any]] = Body(..., example=[
        {
            "trio_numero": 1,
            "passada1_tempo": 45.2,
            "passada2_tempo": 44.8,
            "colocacao": 1,
            "premiacao_bruta": 500.0,
            "no_time": False,
            "desclassificado": False,
            "observacoes": "Importado via CSV"
        }
    ]),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Importa resultados de um arquivo CSV"""
    
    try:
        resultado_importacao = await RepositorioResultado(db).importar_resultados_csv(prova_id, dados_csv)
        
        if resultado_importacao['sucesso']:
            return success_response(
                resultado_importacao,
                f"Importação concluída: {resultado_importacao['resultados_importados']} resultados processados",
                status_code=201
            )
        else:
            return error_response(
                message=f"Erros na importação: {len(resultado_importacao['erros'])} erros encontrados",
                data=resultado_importacao
            )
    except Exception as e:
        return error_response(message=f'Erro na importação: {str(e)}')

# -------------------------- Utilitários e Validações --------------------------

@router.post("/resultado/recalcular/{prova_id}", tags=['Resultado Utilitários'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def recalcular_campos_derivados(
    prova_id: int = Path(..., description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Recalcula todos os campos derivados dos resultados de uma prova"""
    
    try:
        sucesso = await RepositorioResultado(db).recalcular_todos_os_campos(prova_id)
        
        if sucesso:
            return success_response(None, 'Campos derivados recalculados com sucesso')
        else:
            return error_response(message='Erro ao recalcular campos')
    except Exception as e:
        return error_response(message=f'Erro no recálculo: {str(e)}')

@router.get("/resultado/validar-consistencia/{prova_id}", tags=['Resultado Validação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def validar_consistencia_resultados(
    prova_id: int = Path(..., description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Valida consistência dos dados de resultados"""
    
    try:
        validacao = await RepositorioResultado(db).validar_consistencia_resultados(prova_id)
        
        if validacao['valido']:
            return success_response(validacao, 'Dados consistentes - nenhuma inconsistência encontrada')
        else:
            return error_response(
                message=f"Inconsistências encontradas: {validacao['total_inconsistencias']}",
                data=validacao
            )
    except Exception as e:
        return error_response(message=f'Erro na validação: {str(e)}')

@router.post("/resultado/corrigir-tempos", tags=['Resultado Utilitários'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def corrigir_tempos_resultado(
    resultado_id: int = Query(..., description="ID do resultado"),
    passada1_tempo: Optional[float] = Query(default=None, description="Novo tempo da passada 1"),
    passada2_tempo: Optional[float] = Query(default=None, description="Novo tempo da passada 2"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Corrige tempos de um resultado específico e recalcula a média"""
    
    try:
        resultado_data = models.ResultadoPUT(
            passada1_tempo=passada1_tempo,
            passada2_tempo=passada2_tempo
        )
        
        resultado_atualizado = await RepositorioResultado(db).put(resultado_id, resultado_data)
        
        if resultado_atualizado:
            return success_response(resultado_atualizado, 'Tempos corrigidos e média recalculada')
        else:
            return error_response(message='Resultado não encontrado')
    except Exception as e:
        return error_response(message=f'Erro na correção: {str(e)}')

@router.get("/resultado/analise/distribuicao-tempos/{prova_id}", tags=['Resultado Análise'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def analise_distribuicao_tempos(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(default=None, description="ID da categoria (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Análise da distribuição de tempos em uma prova"""
    
    try:
        resultados = await RepositorioResultado(db).get_by_prova(prova_id, categoria_id)
        
        if not resultados:
            return error_response(message='Nenhum resultado encontrado!')
        
        # Análise de distribuição
        tempos_validos = [r.media_tempo for r in resultados if r.media_tempo and not r.no_time]
        
        if not tempos_validos:
            return error_response(message='Nenhum tempo válido encontrado!')
        
        tempos_validos.sort()
        n = len(tempos_validos)
        
        analise = {
            'prova_id': prova_id,
            'categoria_id': categoria_id,
            'total_tempos': n,
            'tempo_minimo': round(min(tempos_validos), 2),
            'tempo_maximo': round(max(tempos_validos), 2),
            'tempo_medio': round(sum(tempos_validos) / n, 2),
            'mediana': round(tempos_validos[n // 2], 2),
            'quartil_1': round(tempos_validos[n // 4], 2),
            'quartil_3': round(tempos_validos[3 * n // 4], 2),
            'amplitude': round(max(tempos_validos) - min(tempos_validos), 2),
            'distribuicao': {
                'ate_40s': len([t for t in tempos_validos if t <= 40]),
                '40_50s': len([t for t in tempos_validos if 40 < t <= 50]),
                '50_60s': len([t for t in tempos_validos if 50 < t <= 60]),
                'acima_60s': len([t for t in tempos_validos if t > 60])
            }
        }
        
        return success_response(analise)
    except Exception as e:
        return error_response(message=f'Erro na análise: {str(e)}')

# -------------------------- Endpoints Especiais --------------------------

@router.post("/resultado/processar-prova-completa", tags=['Resultado Especial'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def processar_prova_completa(
    prova_id: int = Query(..., description="ID da prova"),
    resultados_data: List[Dict[str, Any]] = Body(...),
    calcular_colocacoes: bool = Query(default=True, description="Calcular colocações automaticamente"),
    calcular_pontuacao: bool = Query(default=True, description="Calcular pontuação CONTEP"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Processa uma prova completa: lança resultados, calcula colocações e pontuação"""
    
    try:
        repo = RepositorioResultado(db)
        
        # 1. Lançar resultados
        resultado_lancamento = await repo.lancar_resultados_prova(prova_id, resultados_data)
        
        if not resultado_lancamento['sucesso']:
            return error_response(
                message="Erros no lançamento de resultados",
                data=resultado_lancamento
            )
        
        # 2. Calcular colocações se solicitado
        if calcular_colocacoes:
            await repo.calcular_colocacoes_automaticas(prova_id)
        
        # 3. Calcular pontuação se solicitado
        resultado_pontuacao = {}
        if calcular_pontuacao:
            resultado_pontuacao = await repo.calcular_pontuacao_contep(prova_id)
        
        resumo = {
            'prova_id': prova_id,
            'resultados_processados': resultado_lancamento,
            'colocacoes_calculadas': calcular_colocacoes,
            'pontuacao_calculada': resultado_pontuacao if calcular_pontuacao else None,
            'processamento_completo': True
        }
        
        return success_response(
            resumo,
            f"Prova processada com sucesso: {resultado_lancamento['resultados_criados']} resultados criados",
            status_code=201
        )
        
    except Exception as e:
        return error_response(message=f'Erro no processamento completo: {str(e)}')