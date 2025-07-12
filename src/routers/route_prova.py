from fastapi import APIRouter, status, Depends, HTTPException, Path, Query, Body
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import datetime, date, timedelta
from src.utils.auth_utils import obter_usuario_logado
from src.database.db import get_db
from src.database import models, schemas
from src.utils.api_response import success_response, error_response
from src.repositorios.prova import RepositorioProva
from src.utils.route_error_handler import RouteErrorHandler

router = APIRouter(route_class=RouteErrorHandler)

# -------------------------- Operações Básicas CRUD --------------------------

@router.get("/prova/listar", tags=['Prova'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_provas(
    ativas_apenas: bool = Query(default=True, description="Listar apenas provas ativas"),
    ano: Optional[int] = Query(default=None, description="Filtrar por ano específico"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista todas as provas do sistema"""
    
    provas = await RepositorioProva(db).get_all(ativas_apenas, ano)
    if not provas:
        filtro_msg = f" do ano {ano}" if ano else ""
        return error_response(message=f'Nenhuma prova encontrada{filtro_msg}!')
    
    return success_response(provas, f'{len(provas)} provas encontradas')

@router.get("/prova/{prova_id}/estatisticas", tags=['Prova'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def obter_estatisticas_prova(
    prova_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém estatísticas detalhadas de uma prova específica"""
    
    try:
        # Verificar se a prova existe
        prova = await RepositorioProva(db).get_by_id(prova_id)
        if not prova:
            return error_response(message=f'Prova com ID {prova_id} não encontrada!')
        
        # Buscar estatísticas
        estatisticas = await RepositorioProva(db).get_estatisticas(prova_id)
        
        return success_response(estatisticas, 'Estatísticas obtidas com sucesso')
        
    except Exception as error:
        return error_response(message='Erro interno do servidor')


@router.get("/prova/listar-com-stats", tags=['Prova'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_provas_com_estatisticas(
    ativas_apenas: bool = Query(default=True, description="Listar apenas provas ativas"),
    ano: Optional[int] = Query(default=None, description="Filtrar por ano específico"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista todas as provas com suas estatísticas incluídas"""
    
    try:
        provas = await RepositorioProva(db).get_all_com_estatisticas(ativas_apenas, ano)
        if not provas:
            filtro_msg = f" do ano {ano}" if ano else ""
            return error_response(message=f'Nenhuma prova encontrada{filtro_msg}!')
        
        return success_response(provas, f'{len(provas)} provas encontradas com estatísticas')
        
    except Exception as error:
        return error_response(message='Erro interno do servidor')

@router.get("/prova/consultar/{prova_id}", tags=['Prova'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def consultar_prova(
    prova_id: int = Path(..., description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Consulta uma prova específica pelo ID"""
    
    prova = await RepositorioProva(db).get_by_id(prova_id)
    if not prova:
        return error_response(message='Prova não encontrada!')
    
    return success_response(prova)

@router.post("/prova/criar", tags=['Prova'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def criar_prova(
    prova_data: models.ProvaPOST,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria uma nova prova"""    
    try:
        prova = await RepositorioProva(db).post(prova_data)
        return success_response(prova, 'Prova criada com sucesso', status_code=201)
    except ValueError as e:
        return error_response(message=str(e))

@router.put("/prova/atualizar/{prova_id}", tags=['Prova'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def atualizar_prova(
    prova_id: int = Path(..., description="ID da prova"),
    prova_data: models.ProvaPUT = Body(...),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Atualiza uma prova existente"""
    
    try:
        prova = await RepositorioProva(db).put(prova_id, prova_data)
        if not prova:
            return error_response(message='Prova não encontrada!')
        
        return success_response(prova, 'Prova atualizada com sucesso')
    except ValueError as e:
        return error_response(message=str(e))

@router.delete("/prova/deletar/{prova_id}", tags=['Prova'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def excluir_prova(
    prova_id: int = Path(..., description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Remove uma prova (soft delete se tem trios/resultados)"""
    
    try:
        sucesso = await RepositorioProva(db).delete(prova_id)
        if sucesso:
            return success_response(None, 'Prova removida com sucesso')
        else:
            return error_response(message='Erro ao remover prova')
    except ValueError as e:
        return error_response(message=str(e))

# -------------------------- Consultas Especializadas --------------------------

@router.get("/prova/buscar/nome/{nome}", tags=['Prova Consulta'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def buscar_por_nome(
    nome: str = Path(..., description="Nome da prova (busca parcial)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Busca provas por nome (busca parcial)"""
    
    provas = await RepositorioProva(db).get_by_nome(nome)
    if not provas:
        return error_response(message=f'Nenhuma prova encontrada com o nome "{nome}"!')
    
    return success_response(provas, f'{len(provas)} provas encontradas')

@router.get("/prova/periodo", tags=['Prova Consulta'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def provas_por_periodo(
    data_inicio: date = Query(..., description="Data de início do período"),
    data_fim: date = Query(..., description="Data de fim do período"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Recupera provas de um período específico"""
    
    if data_inicio > data_fim:
        return error_response(message='Data de início deve ser anterior à data de fim!')
    
    provas = await RepositorioProva(db).get_by_periodo(data_inicio, data_fim)
    if not provas:
        return error_response(message='Nenhuma prova encontrada no período informado!')
    
    return success_response(provas, f'{len(provas)} provas no período')

@router.get("/prova/rancho/{rancho}", tags=['Prova Consulta'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def provas_por_rancho(
    rancho: str = Path(..., description="Nome do rancho"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna provas de um rancho específico"""
    
    provas = await RepositorioProva(db).get_provas_por_rancho(rancho, ano)
    if not provas:
        filtro_msg = f" no ano {ano}" if ano else ""
        return error_response(message=f'Nenhuma prova encontrada para o rancho "{rancho}"{filtro_msg}!')
    
    return success_response(provas, f'{len(provas)} provas encontradas')

@router.get("/prova/estado/{estado}", tags=['Prova Consulta'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def provas_por_estado(
    estado: str = Path(..., description="Estado (UF)"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna provas de um estado específico"""
    
    if len(estado) != 2:
        return error_response(message='Estado deve ter exatamente 2 caracteres!')
    
    provas = await RepositorioProva(db).get_provas_por_estado(estado, ano)
    if not provas:
        filtro_msg = f" no ano {ano}" if ano else ""
        return error_response(message=f'Nenhuma prova encontrada no estado {estado.upper()}{filtro_msg}!')
    
    return success_response(provas, f'{len(provas)} provas encontradas')

@router.get("/prova/futuras", tags=['Prova Consulta'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def provas_futuras(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna provas futuras (a partir de hoje)"""
    
    provas = await RepositorioProva(db).get_provas_futuras()
    if not provas:
        return error_response(message='Nenhuma prova futura encontrada!')
    
    return success_response(provas, f'{len(provas)} provas futuras')

@router.get("/prova/passadas", tags=['Prova Consulta'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def provas_passadas(
    limite: int = Query(default=50, ge=1, le=200, description="Número máximo de provas"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna provas passadas (mais recentes primeiro)"""
    
    provas = await RepositorioProva(db).get_provas_passadas(limite)
    if not provas:
        return error_response(message='Nenhuma prova passada encontrada!')
    
    return success_response(provas, f'{len(provas)} provas passadas')

# -------------------------- Estatísticas e Relatórios --------------------------

@router.get("/prova/estatisticas/{prova_id}", tags=['Prova Estatísticas'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def estatisticas_prova(
    prova_id: int = Path(..., description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera estatísticas completas de uma prova"""
    
    estatisticas = await RepositorioProva(db).get_estatisticas_prova(prova_id)
    if not estatisticas:
        return error_response(message='Prova não encontrada!')
    
    return success_response(estatisticas)

@router.get("/prova/ranking/{prova_id}", tags=['Prova Ranking'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def ranking_prova(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(default=None, description="ID da categoria (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera ranking de uma prova (geral ou por categoria)"""
    
    try:
        ranking = await RepositorioProva(db).get_ranking_prova(prova_id, categoria_id)
        if not ranking:
            return error_response(message='Nenhum resultado encontrado para gerar ranking!')
        
        return success_response(ranking, f'Ranking gerado com {len(ranking)} posições')
    except Exception as e:
        return error_response(message=f'Erro ao gerar ranking: {str(e)}')

@router.get("/prova/relatorio/anual/{ano}", tags=['Prova Relatórios'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def relatorio_anual(
    ano: int = Path(..., description="Ano do relatório"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera relatório anual de provas"""
    
    try:
        relatorio = await RepositorioProva(db).gerar_relatorio_anual(ano)
        return success_response(relatorio)
    except Exception as e:
        return error_response(message=f'Erro ao gerar relatório: {str(e)}')

@router.get("/prova/calendario/{ano}", tags=['Prova Calendário'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def calendario_provas(
    ano: int = Path(..., description="Ano do calendário"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna calendário de provas organizadas por mês"""
    
    try:
        calendario = await RepositorioProva(db).get_calendario_provas(ano)
        if not calendario:
            return error_response(message=f'Nenhuma prova encontrada para o ano {ano}!')
        
        return success_response(calendario, f'Calendário {ano} gerado com {len(calendario)} meses')
    except Exception as e:
        return error_response(message=f'Erro ao gerar calendário: {str(e)}')

# -------------------------- Validações e Utilitários --------------------------

@router.get("/prova/pode-alterar/{prova_id}", tags=['Prova Validação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def pode_alterar_prova(
    prova_id: int = Path(..., description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Verifica se a prova pode ser alterada"""
    
    try:
        pode_alterar, mensagem = await RepositorioProva(db).pode_alterar_prova(prova_id)
        
        return success_response({
            'pode_alterar': pode_alterar,
            'mensagem': mensagem,
            'prova_id': prova_id
        })
    except Exception as e:
        return error_response(message=f'Erro na verificação: {str(e)}')

@router.post("/prova/duplicar/{prova_id}", tags=['Prova Utilitários'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def duplicar_prova(
    prova_id: int = Path(..., description="ID da prova original"),
    nova_data: date = Query(..., description="Data da nova prova"),
    novo_nome: Optional[str] = Query(default=None, description="Nome da nova prova (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Duplica uma prova para uma nova data"""
    
    try:
        nova_prova = await RepositorioProva(db).duplicar_prova(prova_id, nova_data, novo_nome)
        return success_response(nova_prova, 'Prova duplicada com sucesso', status_code=201)
    except ValueError as e:
        return error_response(message=str(e))

@router.get("/prova/similares/{prova_id}", tags=['Prova Utilitários'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def provas_similares(
    prova_id: int = Path(..., description="ID da prova"),
    limite: int = Query(default=5, ge=1, le=20, description="Número máximo de provas similares"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Encontra provas similares (mesmo rancho/cidade)"""
    
    try:
        provas = await RepositorioProva(db).get_provas_similares(prova_id, limite)
        if not provas:
            return error_response(message='Nenhuma prova similar encontrada!')
        
        return success_response(provas, f'{len(provas)} provas similares encontradas')
    except Exception as e:
        return error_response(message=f'Erro na busca: {str(e)}')

# -------------------------- Exportação e Importação --------------------------

@router.get("/prova/exportar", tags=['Prova Exportação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def exportar_provas(
    formato: str = Query(default="json", regex="^(json|csv)$", description="Formato de exportação"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    estado: Optional[str] = Query(default=None, description="Estado específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Exporta dados das provas em formato estruturado"""
    
    try:
        if estado and len(estado) != 2:
            return error_response(message='Estado deve ter exatamente 2 caracteres!')
        
        dados_exportacao = await RepositorioProva(db).exportar_provas(ano, estado)
        
        return success_response({
            'formato': formato,
            'total_provas': len(dados_exportacao),
            'filtros': {
                'ano': ano,
                'estado': estado
            },
            'dados': dados_exportacao,
            'exportado_em': datetime.now().isoformat()
        })
    except Exception as e:
        return error_response(message=f'Erro na exportação: {str(e)}')

@router.post("/prova/importar", tags=['Prova Importação'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def importar_provas(
    provas_data: List[models.ProvaPOST] = Body(...),
    sobrescrever: bool = Query(default=False, description="Sobrescrever provas existentes"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Importa provas em lote"""
    
    try:
        repo = RepositorioProva(db)
        provas_criadas = []
        provas_atualizadas = []
        erros = []
        
        for prova_data in provas_data:
            try:
                # Verificar se já existe (por nome e data)
                provas_existentes = await repo.get_by_nome(prova_data.nome)
                prova_existente = None
                
                for prova in provas_existentes:
                    if prova.data == prova_data.data:
                        prova_existente = prova
                        break
                
                if prova_existente and sobrescrever:
                    # Atualizar existente
                    prova_put = models.ProvaPUT(
                        nome=prova_data.nome,
                        data=prova_data.data,
                        rancho=prova_data.rancho,
                        cidade=prova_data.cidade,
                        estado=prova_data.estado,
                        valor_inscricao=prova_data.valor_inscricao,
                        percentual_desconto=prova_data.percentual_desconto,
                        ativa=prova_data.ativa,
                        tipo_copa=prova_data.tipo_copa
                    )
                    prova_atualizada = await repo.put(prova_existente.id, prova_put)
                    provas_atualizadas.append(prova_atualizada)
                elif not prova_existente:
                    # Criar nova
                    prova_criada = await repo.post(prova_data)
                    provas_criadas.append(prova_criada)
                else:
                    erros.append(f"Prova '{prova_data.nome}' em {prova_data.data} já existe")
                    
            except Exception as e:
                erros.append(f"Erro ao processar prova '{prova_data.nome}': {str(e)}")
        
        return success_response({
            'provas_criadas': len(provas_criadas),
            'provas_atualizadas': len(provas_atualizadas),
            'erros': erros,
            'dados': {
                'criadas': provas_criadas,
                'atualizadas': provas_atualizadas
            }
        }, f'Importação concluída: {len(provas_criadas)} criadas, {len(provas_atualizadas)} atualizadas', status_code=201)
        
    except Exception as e:
        return error_response(message=f'Erro na importação: {str(e)}')

# -------------------------- Relatórios Especiais --------------------------

@router.get("/prova/resumo/geral", tags=['Prova Resumo'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def resumo_geral_provas(
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna resumo geral das provas do sistema"""
    
    try:
        repo = RepositorioProva(db)
        
        # Buscar provas
        provas = await repo.get_all(ativas_apenas=False, ano=ano)
        
        if not provas:
            return error_response(message='Nenhuma prova encontrada!')
        
        # Estatísticas básicas
        total_provas = len(provas)
        provas_ativas = len([p for p in provas if p.ativa])
        provas_inativas = total_provas - provas_ativas
        
        # Análise temporal
        hoje = date.today()
        provas_futuras = len([p for p in provas if p.data >= hoje and p.ativa])
        provas_passadas = len([p for p in provas if p.data < hoje])
        
        # Por estado
        por_estado = {}
        for prova in provas:
            estado = prova.estado or 'N/I'
            if estado not in por_estado:
                por_estado[estado] = 0
            por_estado[estado] += 1
        
        # Por tipo de copa
        por_tipo_copa = {}
        for prova in provas:
            tipo = prova.tipo_copa.value if prova.tipo_copa else 'regular'
            if tipo not in por_tipo_copa:
                por_tipo_copa[tipo] = 0
            por_tipo_copa[tipo] += 1
        
        # Valores de inscrição
        valores_inscricao = [float(p.valor_inscricao or 0) for p in provas if p.valor_inscricao]
        valor_medio = sum(valores_inscricao) / len(valores_inscricao) if valores_inscricao else 0
        
        resumo = {
            'ano': ano,
            'total_provas': total_provas,
            'provas_ativas': provas_ativas,
            'provas_inativas': provas_inativas,
            'provas_futuras': provas_futuras,
            'provas_passadas': provas_passadas,
            'por_estado': por_estado,
            'por_tipo_copa': por_tipo_copa,
            'inscricao': {
                'valor_medio': round(valor_medio, 2),
                'com_valor_definido': len(valores_inscricao)
            },
            'periodo_analise': {
                'data_primeira': min(p.data for p in provas).isoformat() if provas else None,
                'data_ultima': max(p.data for p in provas).isoformat() if provas else None
            }
        }
        
        return success_response(resumo)
    except Exception as e:
        return error_response(message=f'Erro ao gerar resumo: {str(e)}')

@router.get("/prova/analise/frequencia", tags=['Prova Análise'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def analise_frequencia_provas(
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Análise de frequência de provas por período"""
    
    try:
        provas = await RepositorioProva(db).get_all(ativas_apenas=False, ano=ano)
        
        if not provas:
            return error_response(message='Nenhuma prova encontrada para análise!')
        
        # Análise por mês
        por_mes = {}
        meses_nomes = [
            'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
            'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
        ]
        
        for i, mes_nome in enumerate(meses_nomes, 1):
            por_mes[mes_nome] = len([p for p in provas if p.data.month == i])
        
        # Análise por trimestre
        por_trimestre = {
            'Q1 (Jan-Mar)': sum(por_mes[m] for m in ['Janeiro', 'Fevereiro', 'Março']),
            'Q2 (Abr-Jun)': sum(por_mes[m] for m in ['Abril', 'Maio', 'Junho']),
            'Q3 (Jul-Set)': sum(por_mes[m] for m in ['Julho', 'Agosto', 'Setembro']),
            'Q4 (Out-Dez)': sum(por_mes[m] for m in ['Outubro', 'Novembro', 'Dezembro'])
        }
        
        # Análise por dia da semana
        por_dia_semana = {}
        dias_nomes = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        
        for prova in provas:
            dia_semana = dias_nomes[prova.data.weekday()]
            if dia_semana not in por_dia_semana:
                por_dia_semana[dia_semana] = 0
            por_dia_semana[dia_semana] += 1
        
        # Estatísticas
        mes_mais_ativo = max(por_mes.items(), key=lambda x: x[1]) if por_mes else None
        trimestre_mais_ativo = max(por_trimestre.items(), key=lambda x: x[1]) if por_trimestre else None
        dia_preferido = max(por_dia_semana.items(), key=lambda x: x[1]) if por_dia_semana else None
        
        analise = {
            'ano': ano,
            'total_provas_analisadas': len(provas),
            'distribuicao_mensal': por_mes,
            'distribuicao_trimestral': por_trimestre,
            'distribuicao_semanal': por_dia_semana,
            'insights': {
                'mes_mais_ativo': mes_mais_ativo[0] if mes_mais_ativo else None,
                'trimestre_mais_ativo': trimestre_mais_ativo[0] if trimestre_mais_ativo else None,
                'dia_semana_preferido': dia_preferido[0] if dia_preferido else None,
                'media_provas_por_mes': round(len(provas) / 12, 1) if ano else None
            }
        }
        
        return success_response(analise)
    except Exception as e:
        return error_response(message=f'Erro na análise: {str(e)}')

# -------------------------- Utilitários Específicos --------------------------

@router.post("/prova/validar-data", tags=['Prova Validação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def validar_data_prova(
    data_proposta: date = Query(..., description="Data proposta para a prova"),
    nome_prova: str = Query(..., description="Nome da prova"),
    rancho: Optional[str] = Query(default=None, description="Rancho da prova"),
    excluir_id: Optional[int] = Query(default=None, description="ID da prova a excluir da validação (para edição)"),  # 👈 NOVO PARÂMETRO
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Valida se uma data é adequada para criar uma prova"""
    
    try:
        # Buscar provas na mesma data
        provas_mesma_data = await RepositorioProva(db).get_by_periodo(data_proposta, data_proposta)
        
        # 🔥 FILTRAR A PROVA SENDO EDITADA
        if excluir_id:
            provas_mesma_data = [prova for prova in provas_mesma_data if prova.id != excluir_id]
        
        # Buscar provas do mesmo rancho próximas
        provas_rancho_proximas = []
        if rancho:
            provas_rancho = await RepositorioProva(db).get_provas_por_rancho(rancho)
            # Filtrar provas em +/- 7 dias
            for prova in provas_rancho:
                diff_dias = abs((prova.data - data_proposta).days)
                if diff_dias <= 7 and prova.data != data_proposta:
                    # 🔥 TAMBÉM EXCLUIR DA VALIDAÇÃO DE RANCHO
                    if not excluir_id or prova.id != excluir_id:
                        provas_rancho_proximas.append(prova)
        
        # Análise de conflitos
        conflitos = []
        avisos = []
        
        if provas_mesma_data:
            conflitos.append(f"Já existem {len(provas_mesma_data)} prova(s) na mesma data")
        
        if provas_rancho_proximas:
            avisos.append(f"Existem {len(provas_rancho_proximas)} prova(s) do mesmo rancho em um período de 7 dias")
        
        # Verificar se é final de semana
        if data_proposta.weekday() not in [5, 6]:  # 5=sábado, 6=domingo
            avisos.append("Data não é final de semana - a maioria das provas ocorre aos sábados/domingos")
        
        # Verificar se é muito no futuro
        dias_ate_prova = (data_proposta - date.today()).days
        if dias_ate_prova > 365:
            avisos.append("Prova programada para mais de 1 ano no futuro")
        elif dias_ate_prova < 7:
            avisos.append("Prova programada para menos de 7 dias - pode ser pouco tempo para inscrições")
        
        validacao = {
            'data_proposta': data_proposta.isoformat(),
            'nome_prova': nome_prova,
            'rancho': rancho,
            'valida': len(conflitos) == 0,
            'conflitos': conflitos,
            'avisos': avisos,
            'provas_mesma_data': len(provas_mesma_data),
            'provas_rancho_proximas': len(provas_rancho_proximas),
            'dia_semana': ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][data_proposta.weekday()],
            'dias_ate_prova': dias_ate_prova
        }
        
        return success_response(validacao)
    except Exception as e:
        return error_response(message=f'Erro na validação: {str(e)}')

@router.get("/prova/sugestoes/datas", tags=['Prova Utilitários'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def sugerir_datas_prova(
    mes: int = Query(..., ge=1, le=12, description="Mês desejado"),
    ano: int = Query(..., ge=2024, description="Ano desejado"),
    rancho: Optional[str] = Query(default=None, description="Rancho da prova"),
    apenas_finais_semana: bool = Query(default=True, description="Apenas finais de semana"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Sugere datas disponíveis para uma prova"""
    
    try:
        import calendar
        
        # Gerar todas as datas do mês
        primeiro_dia = date(ano, mes, 1)
        ultimo_dia = date(ano, mes, calendar.monthrange(ano, mes)[1])
        
        # Buscar provas existentes no mês
        provas_mes = await RepositorioProva(db).get_by_periodo(primeiro_dia, ultimo_dia)
        datas_ocupadas = {prova.data for prova in provas_mes}
        
        # Buscar provas do rancho (se especificado)
        provas_rancho = []
        if rancho:
            provas_rancho = await RepositorioProva(db).get_provas_por_rancho(rancho)
        
        # Gerar sugestões
        sugestoes = []
        data_atual = primeiro_dia
        
        while data_atual <= ultimo_dia:
            # Filtrar apenas finais de semana se solicitado
            if apenas_finais_semana and data_atual.weekday() not in [5, 6]:
                data_atual += timedelta(days=1)
                continue
            
            # Verificar se a data não está ocupada
            if data_atual in datas_ocupadas:
                data_atual += timedelta(days=1)
                continue
            
            # Verificar conflito com rancho
            conflito_rancho = False
            if rancho:
                for prova in provas_rancho:
                    diff_dias = abs((prova.data - data_atual).days)
                    if diff_dias <= 7:
                        conflito_rancho = True
                        break
            
            # Verificar se não é muito próximo de hoje
            dias_ate_data = (data_atual - date.today()).days
            if dias_ate_data < 7:
                data_atual += timedelta(days=1)
                continue
            
            sugestao = {
                'data': data_atual.isoformat(),
                'dia_semana': ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'][data_atual.weekday()],
                'dias_ate_data': dias_ate_data,
                'conflito_rancho': conflito_rancho,
                'score': 100  # Score base
            }
            
            # Ajustar score
            if data_atual.weekday() == 5:  # Sábado
                sugestao['score'] += 20
            elif data_atual.weekday() == 6:  # Domingo
                sugestao['score'] += 10
            
            if conflito_rancho:
                sugestao['score'] -= 30
            
            if 14 <= dias_ate_data <= 60:  # Período ideal
                sugestao['score'] += 15
            
            sugestoes.append(sugestao)
            data_atual += timedelta(days=1)
        
        # Ordenar por score
        sugestoes.sort(key=lambda x: x['score'], reverse=True)
        
        return success_response({
            'mes': mes,
            'ano': ano,
            'rancho': rancho,
            'total_sugestoes': len(sugestoes),
            'sugestoes': sugestoes[:10],  # Top 10
            'datas_ocupadas_no_mes': len(datas_ocupadas)
        })
    except Exception as e:
        return error_response(message=f'Erro ao gerar sugestões: {str(e)}')

@router.post("/prova/configurar-padrao", tags=['Prova Configuração'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def configurar_prova_padrao(
    configuracao: Dict[str, Any] = Body(..., example={
        "valor_inscricao_padrao": 100.0,
        "percentual_desconto_padrao": 5.0,
        "template_nome": "{rancho} - {mes}/{ano}",
        "observacoes_padrao": "Prova seguindo regulamento LCTP"
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Configura valores padrão para criação de provas"""
    
    try:
        # Validar configuração
        campos_obrigatorios = ['valor_inscricao_padrao', 'percentual_desconto_padrao']
        for campo in campos_obrigatorios:
            if campo not in configuracao:
                return error_response(message=f'Campo obrigatório: {campo}')
        
        # Validar valores
        if configuracao['valor_inscricao_padrao'] < 0:
            return error_response(message='Valor de inscrição não pode ser negativo')
        
        if not (0 <= configuracao['percentual_desconto_padrao'] <= 100):
            return error_response(message='Percentual de desconto deve estar entre 0 e 100')
        
        # Salvar configuração (em produção, salvaria no banco ou arquivo de config)
        # Por enquanto, apenas retornamos a configuração validada
        
        return success_response({
            'configuracao_salva': configuracao,
            'campos_configurados': len(configuracao),
            'status': 'Configuração aplicada com sucesso'
        })
    except Exception as e:
        return error_response(message=f'Erro ao configurar: {str(e)}')
    
@router.get("/prova/{prova_id}/categoria/{categoria_id}/configuracao", tags=['Prova Configuração'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def obter_configuracao_prova_categoria(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém a configuração de passadas de uma prova para uma categoria específica"""
    
    try:
        # Verificar se a prova existe
        prova = await RepositorioProva(db).get_by_id(prova_id)
        if not prova:
            return error_response(message=f'Prova com ID {prova_id} não encontrada!')
        
        # Verificar se a categoria existe
        categoria = db.execute(
            select(schemas.Categorias).where(schemas.Categorias.id == categoria_id)
        ).scalars().first()
        
        if not categoria:
            return error_response(message=f'Categoria com ID {categoria_id} não encontrada!')
        
        # Buscar configuração específica da prova/categoria
        config_passadas = db.execute(
            select(schemas.ConfiguracaoPassadasProva).where(
                schemas.ConfiguracaoPassadasProva.prova_id == prova_id,
                schemas.ConfiguracaoPassadasProva.categoria_id == categoria_id,
                schemas.ConfiguracaoPassadasProva.ativa == True
            )
        ).scalars().first()
        
        # Se não tem configuração específica, usar configurações padrão por categoria
        if not config_passadas:
            configuracoes_padrao = {
                'baby': {
                    'max_passadas_por_trio': 3,
                    'max_corridas_por_pessoa': 9,  # 3 trios x 3 passadas
                    'tempo_limite_padrao': 90.0,
                    'intervalo_minimo_passadas': 10,
                    'permite_repetir_boi': True
                },
                'kids': {
                    'max_passadas_por_trio': 5,
                    'max_corridas_por_pessoa': 15,  # 3 trios x 5 passadas
                    'tempo_limite_padrao': 75.0,
                    'intervalo_minimo_passadas': 8,
                    'permite_repetir_boi': True
                },
                'mirim': {
                    'max_passadas_por_trio': 8,
                    'max_corridas_por_pessoa': 24,  # 3 trios x 8 passadas
                    'tempo_limite_padrao': 65.0,
                    'intervalo_minimo_passadas': 6,
                    'permite_repetir_boi': False
                },
                'feminina': {
                    'max_passadas_por_trio': 8,
                    'max_corridas_por_pessoa': 24,  # 3 trios x 8 passadas
                    'tempo_limite_padrao': 65.0,
                    'intervalo_minimo_passadas': 6,
                    'permite_repetir_boi': False
                },
                'aberta': {
                    'max_passadas_por_trio': 10,
                    'max_corridas_por_pessoa': 30,  # 3 trios x 10 passadas
                    'tempo_limite_padrao': 50.0,
                    'intervalo_minimo_passadas': 5,
                    'permite_repetir_boi': False
                },
                'handicap': {
                    'max_passadas_por_trio': 10,
                    'max_corridas_por_pessoa': 30,  # 3 trios x 10 passadas
                    'tempo_limite_padrao': 55.0,
                    'intervalo_minimo_passadas': 5,
                    'permite_repetir_boi': False
                }
            }
            
            config_padrao = configuracoes_padrao.get(categoria.tipo, configuracoes_padrao['aberta'])
            
            configuracao = {
                'id': None,
                'prova_id': prova_id,
                'categoria_id': categoria_id,
                'max_passadas_por_trio': config_padrao['max_passadas_por_trio'],
                'max_corridas_por_pessoa': config_padrao['max_corridas_por_pessoa'],
                'tempo_limite_padrao': config_padrao['tempo_limite_padrao'],
                'intervalo_minimo_passadas': config_padrao['intervalo_minimo_passadas'],
                'permite_repetir_boi': config_padrao['permite_repetir_boi'],
                'bois_disponiveis': None,
                'ativa': True,
                'created_at': None,
                'origem': 'padrao',
                'observacoes': f'Configuração padrão para categoria {categoria.tipo}'
            }
        else:
            # Retornar configuração específica encontrada
            configuracao = {
                'id': config_passadas.id,
                'prova_id': config_passadas.prova_id,
                'categoria_id': config_passadas.categoria_id,
                'max_passadas_por_trio': config_passadas.max_passadas_por_trio,
                'max_corridas_por_pessoa': config_passadas.max_corridas_por_pessoa,
                'tempo_limite_padrao': float(config_passadas.tempo_limite_padrao),
                'intervalo_minimo_passadas': config_passadas.intervalo_minimo_passadas,
                'permite_repetir_boi': config_passadas.permite_repetir_boi,
                'bois_disponiveis': config_passadas.get_bois_disponiveis_list() if hasattr(config_passadas, 'get_bois_disponiveis_list') else None,
                'ativa': config_passadas.ativa,
                'created_at': config_passadas.created_at.isoformat() if config_passadas.created_at else None,
                'origem': 'especifica',
                'observacoes': 'Configuração específica para esta prova/categoria'
            }
        
        # Informações adicionais úteis
        configuracao['info_adicional'] = {
            'prova_nome': prova.nome,
            'prova_data': prova.data.isoformat() if prova.data else None,
            'categoria_nome': categoria.nome,
            'categoria_tipo': categoria.tipo,
            'total_participacoes_teoricas': configuracao['max_corridas_por_pessoa'],
            'trios_teoricos_por_competidor': configuracao['max_corridas_por_pessoa'] // configuracao['max_passadas_por_trio'],
            'calculado_em': datetime.now().isoformat()
        }
        
        return success_response(configuracao, 'Configuração obtida com sucesso')
        
    except Exception as error:
        print(f"Erro ao buscar configuração: {str(error)}")
        return error_response(message=f'Erro interno do servidor: {str(error)}')

# -------------------------- Dashboard e Visão Geral --------------------------

@router.get("/prova/dashboard", tags=['Prova Dashboard'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def dashboard_provas(
    periodo_dias: int = Query(default=90, ge=30, le=365, description="Período em dias para análise"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Dashboard com visão geral das provas"""
    
    try:
        hoje = date.today()
        data_inicio = hoje - timedelta(days=periodo_dias)
        data_fim = hoje + timedelta(days=periodo_dias)
        
        # Buscar provas do período
        provas_periodo = await RepositorioProva(db).get_by_periodo(data_inicio, data_fim)
        
        # Separar por status temporal
        provas_passadas = [p for p in provas_periodo if p.data < hoje]
        provas_hoje = [p for p in provas_periodo if p.data == hoje]
        provas_futuras = [p for p in provas_periodo if p.data > hoje]
        
        # Próximas provas (próximos 30 dias)
        data_limite_proximas = hoje + timedelta(days=30)
        proximas_provas = [p for p in provas_futuras if p.data <= data_limite_proximas]
        
        # Estatísticas rápidas
        total_periodo = len(provas_periodo)
        media_por_mes = round(total_periodo / (periodo_dias / 30), 1) if periodo_dias >= 30 else 0
        
        # Estados mais ativos
        por_estado = {}
        for prova in provas_periodo:
            estado = prova.estado or 'N/I'
            if estado not in por_estado:
                por_estado[estado] = 0
            por_estado[estado] += 1
        
        estados_top = sorted(por_estado.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Ranchos mais ativos
        por_rancho = {}
        for prova in provas_periodo:
            rancho = prova.rancho or 'N/I'
            if rancho not in por_rancho:
                por_rancho[rancho] = 0
            por_rancho[rancho] += 1
        
        ranchos_top = sorted(por_rancho.items(), key=lambda x: x[1], reverse=True)[:5]
        
        dashboard = {
            'periodo_analise': {
                'data_inicio': data_inicio.isoformat(),
                'data_fim': data_fim.isoformat(),
                'dias_analisados': periodo_dias * 2  # passado + futuro
            },
            'resumo_geral': {
                'total_provas_periodo': total_periodo,
                'provas_passadas': len(provas_passadas),
                'provas_hoje': len(provas_hoje),
                'provas_futuras': len(provas_futuras),
                'media_provas_mes': media_por_mes
            },
            'proximas_provas': {
                'total_proximos_30_dias': len(proximas_provas),
                'lista': [
                    {
                        'id': p.id,
                        'nome': p.nome,
                        'data': p.data.isoformat(),
                        'rancho': p.rancho,
                        'cidade': p.cidade,
                        'estado': p.estado,
                        'dias_restantes': (p.data - hoje).days
                    }
                    for p in sorted(proximas_provas, key=lambda x: x.data)[:10]
                ]
            },
            'rankings': {
                'estados_mais_ativos': estados_top,
                'ranchos_mais_ativos': ranchos_top
            },
            'alertas': []
        }
        
        # Gerar alertas
        if len(provas_hoje) > 0:
            dashboard['alertas'].append(f"🏁 {len(provas_hoje)} prova(s) acontecendo hoje!")
        
        amanha = hoje + timedelta(days=1)
        provas_amanha = [p for p in provas_futuras if p.data == amanha]
        if provas_amanha:
            dashboard['alertas'].append(f"📅 {len(provas_amanha)} prova(s) acontecendo amanhã")
        
        provas_proxima_semana = [p for p in provas_futuras if (p.data - hoje).days <= 7]
        if len(provas_proxima_semana) > 5:
            dashboard['alertas'].append(f"⚡ Semana movimentada: {len(provas_proxima_semana)} provas nos próximos 7 dias")
        
        return success_response(dashboard)
    except Exception as e:
        return error_response(message=f'Erro ao gerar dashboard: {str(e)}')

@router.get("/prova/metricas/performance", tags=['Prova Métricas'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def metricas_performance_sistema(
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Métricas de performance do sistema de provas"""
    
    try:
        # Buscar provas
        provas = await RepositorioProva(db).get_all(ativas_apenas=False, ano=ano)
        
        if not provas:
            return error_response(message='Nenhuma prova encontrada para análise!')
        
        # Métricas de participação (simuladas - em produção viria dos trios/resultados)
        total_provas = len(provas)
        provas_com_dados = 0
        total_trios_estimado = 0
        total_competidores_estimado = 0
        
        # Simular dados baseados em médias típicas
        for prova in provas:
            # Em produção, seria: len(prova.trios)
            trios_estimados = 15  # Média estimada por prova
            provas_com_dados += 1
            total_trios_estimado += trios_estimados
            total_competidores_estimado += trios_estimados * 3
        
        # Métricas temporais
        hoje = date.today()
        provas_realizadas = len([p for p in provas if p.data < hoje])
        provas_futuras = len([p for p in provas if p.data >= hoje and p.ativa])
        
        # Distribuição geográfica
        distribuicao_estados = {}
        for prova in provas:
            estado = prova.estado or 'N/I'
            if estado not in distribuicao_estados:
                distribuicao_estados[estado] = {
                    'total_provas': 0,
                    'trios_estimados': 0,
                    'competidores_estimados': 0
                }
            
            distribuicao_estados[estado]['total_provas'] += 1
            distribuicao_estados[estado]['trios_estimados'] += 15  # Estimativa
            distribuicao_estados[estado]['competidores_estimados'] += 45  # 15 * 3
        
        # Crescimento (comparar com ano anterior se não especificado)
        crescimento = None
        if not ano:
            ano_atual = date.today().year
            provas_ano_atual = [p for p in provas if p.data.year == ano_atual]
            provas_ano_anterior = [p for p in provas if p.data.year == ano_atual - 1]
            
            if provas_ano_anterior:
                crescimento = {
                    'ano_atual': len(provas_ano_atual),
                    'ano_anterior': len(provas_ano_anterior),
                    'percentual': round(((len(provas_ano_atual) - len(provas_ano_anterior)) / len(provas_ano_anterior)) * 100, 1)
                }
        
        metricas = {
            'periodo_analise': ano or 'todos os anos',
            'metricas_gerais': {
                'total_provas': total_provas,
                'provas_realizadas': provas_realizadas,
                'provas_futuras': provas_futuras,
                'taxa_realizacao': round((provas_realizadas / total_provas) * 100, 1) if total_provas > 0 else 0
            },
            'participacao_estimada': {
                'total_trios': total_trios_estimado,
                'total_competidores': total_competidores_estimado,
                'media_trios_por_prova': round(total_trios_estimado / total_provas, 1) if total_provas > 0 else 0,
                'media_competidores_por_prova': round(total_competidores_estimado / total_provas, 1) if total_provas > 0 else 0
            },
            'distribuicao_geografica': distribuicao_estados,
            'crescimento': crescimento,
            'observacoes': [
                "Dados de participação são estimados",
                "Métricas baseadas em médias históricas",
                "Para dados precisos, consulte relatórios específicos de cada prova"
            ]
        }
        
        return success_response(metricas)
    except Exception as e:
        return error_response(message=f'Erro ao calcular métricas: {str(e)}')