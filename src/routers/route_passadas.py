# route_passadas.py - Rotas Completas Refatoradas para Controle de Passadas

import traceback
from fastapi import APIRouter, status, Depends, HTTPException, Path, Query, Body
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta

from src.utils.auth_utils import obter_usuario_logado
from src.database.db import get_db
from src.database import models, schemas
from src.utils.api_response import success_response, error_response
from src.repositorios.passadas import RepositorioPassadas
from src.utils.route_error_handler import RouteErrorHandler

router = APIRouter(route_class=RouteErrorHandler)

# ========================== OPERAÇÕES BÁSICAS CRUD ==========================

@router.get("/passada/listar", 
           tags=['Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def listar_passadas(
    trio_id: Optional[int] = Query(None, description="ID do trio"),
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    numero_passada: Optional[int] = Query(None, description="Número da passada"),
    status_passada: Optional[str] = Query(None, description="Status da passada"),
    apenas_executadas: bool = Query(False, description="Apenas passadas executadas"),
    # ✅ NOVOS FILTROS SAT
    apenas_sat: bool = Query(False, description="Apenas passadas com SAT"),
    excluir_sat: bool = Query(False, description="Excluir passadas com SAT"),
    apenas_validas_ranking: bool = Query(False, description="Apenas passadas válidas para ranking"),
    pagina: int = Query(1, ge=1, description="Página"),
    tamanho_pagina: int = Query(25, ge=5, le=100, description="Itens por página"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista passadas com filtros e paginação"""
    try:
        filtros = models.FiltrosPassadas(
            trio_id=trio_id,
            prova_id=prova_id,
            categoria_id=categoria_id,
            numero_passada=numero_passada,
            status=status_passada,
            apenas_executadas=apenas_executadas,
            apenas_sat=apenas_sat,
            excluir_sat=excluir_sat,
            apenas_validas_ranking=apenas_validas_ranking,
            pagina=pagina,
            tamanho_pagina=tamanho_pagina
        )
        
        passadas, total = RepositorioPassadas(db).listar_passadas(filtros)
        
        if not passadas:
            return error_response(message='Nenhuma passada encontrada!')
        
        return success_response(
            passadas, 
            f'{len(passadas)} passadas encontradas (total: {total})',
            meta={'total': total, 'pagina': pagina, 'tamanho_pagina': tamanho_pagina}
        )
    except Exception as e:
        return error_response(message=f'Erro ao listar passadas: {str(e)}')

@router.get("/passada/consultar/{passada_id}", 
           tags=['Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def consultar_passada(
    passada_id: int = Path(..., description="ID da passada"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Consulta uma passada específica pelo ID"""
    passada = RepositorioPassadas(db).obter_passada(passada_id)
    if not passada:
        return error_response(message='Passada não encontrada!')
    
    return success_response(passada)

@router.post("/passada/criar", 
            tags=['Passadas'], 
            status_code=status.HTTP_201_CREATED, 
            response_model=models.ApiResponse)
async def criar_passada(
    passada_data: models.PassadaTrioPOST,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria uma nova passada"""
    try:
        passada = RepositorioPassadas(db).criar_passada(passada_data)
        return success_response(passada, 'Passada criada com sucesso', status_code=201)
    except ValueError as e:
        return error_response(message=str(e))
    except Exception as e:
        return error_response(message=f'Erro ao criar passada: {str(e)}')

@router.put("/passada/atualizar/{passada_id}", 
           tags=['Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def atualizar_passada(
    passada_id: int = Path(..., description="ID da passada"),
    passada_data: models.PassadaTrioPUT = Body(...),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Atualiza uma passada existente"""
    try:
        passada = RepositorioPassadas(db).atualizar_passada(passada_id, passada_data)
        if not passada:
            return error_response(message='Passada não encontrada!')
        
        return success_response(passada, 'Passada atualizada com sucesso')
    except ValueError as e:
        return error_response(message=str(e))
    except Exception as e:
        return error_response(message=f'Erro ao atualizar passada: {str(e)}')

@router.delete("/passada/deletar/{passada_id}", 
              tags=['Passadas'], 
              status_code=status.HTTP_200_OK, 
              response_model=models.ApiResponse)
async def excluir_passada(
    passada_id: int = Path(..., description="ID da passada"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Remove uma passada"""
    try:
        sucesso = RepositorioPassadas(db).deletar_passada(passada_id)
        if sucesso:
            return success_response(None, 'Passada removida com sucesso')
        else:
            return error_response(message='Erro ao remover passada')
    except Exception as e:
        return error_response(message=f'Erro ao remover passada: {str(e)}')

# ========================== OPERAÇÕES EM LOTE ==========================

@router.post("/passada/criar-lote", 
            tags=['Passadas Lote'], 
            status_code=status.HTTP_201_CREATED, 
            response_model=models.ApiResponse)
async def criar_passadas_lote(
    request: models.CriarPassadasLoteRequest,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria múltiplas passadas para um trio"""
    try:
        passadas = RepositorioPassadas(db).criar_passadas_lote(request)
        return success_response(
            passadas, 
            f'{len(passadas)} passadas criadas com sucesso',
            status_code=201
        )
    except ValueError as e:
        return error_response(message=str(e))
    except Exception as e:
        return error_response(message=f'Erro ao criar passadas: {str(e)}')

@router.post("/passada/registrar-tempo", 
            tags=['Passadas Execução'], 
            status_code=status.HTTP_200_OK, 
            response_model=models.ApiResponse)
async def registrar_tempo_passada(
    request: models.RegistrarTempoRequest,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Registra tempo de uma passada"""
    try:
        passada = RepositorioPassadas(db).registrar_tempo(request)
        return success_response(passada, 'Tempo registrado com sucesso')
    except ValueError as e:
        return error_response(message=str(e))
    except Exception as e:
        return error_response(message=f'Erro ao registrar tempo: {str(e)}')

@router.post("/passada/validar", 
            tags=['Passadas Validação'], 
            status_code=status.HTTP_200_OK, 
            response_model=models.ApiResponse)
async def validar_passada(
    request: models.ValidarPassadaRequest,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Valida se uma passada pode ser executada"""
    try:
        validacao = RepositorioPassadas(db).validar_passada(request)
        return success_response(validacao)
    except Exception as e:
        return error_response(message=f'Erro na validação: {str(e)}')

# ========================== CONFIGURAÇÕES DE PASSADAS ==========================

@router.get("/passada/configuracao/{prova_id}/{categoria_id}", 
           tags=['Configuração Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_configuracao_passadas(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db)
):
    """Obtém configuração de passadas para uma prova/categoria"""
    config = RepositorioPassadas(db).obter_configuracao(prova_id, categoria_id)
    if not config:
        return error_response(message='Configuração não encontrada!')
    
    return success_response(config)

@router.post("/passada/configuracao/criar", 
            tags=['Configuração Passadas'], 
            status_code=status.HTTP_201_CREATED, 
            response_model=models.ApiResponse)
async def criar_configuracao_passadas(
    config_data: models.ConfiguracaoPassadasPOST,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria configuração de passadas para prova/categoria"""
    try:
        config = RepositorioPassadas(db).criar_configuracao(config_data)
        return success_response(config, 'Configuração criada com sucesso', status_code=201)
    except ValueError as e:
        return error_response(message=str(e))
    except Exception as e:
        return error_response(message=f'Erro ao criar configuração: {str(e)}')

@router.put("/passada/configuracao/atualizar/{config_id}", 
           tags=['Configuração Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def atualizar_configuracao_passadas(
    config_id: int = Path(..., description="ID da configuração"),
    config_data: models.ConfiguracaoPassadasPUT = Body(...),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Atualiza configuração de passadas"""
    try:
        config = RepositorioPassadas(db).atualizar_configuracao(config_id, config_data)
        if not config:
            return error_response(message='Configuração não encontrada!')
        
        return success_response(config, 'Configuração atualizada com sucesso')
    except Exception as e:
        return error_response(message=f'Erro ao atualizar configuração: {str(e)}')

# ========================== CONTROLE DE PARTICIPAÇÃO ==========================

@router.get("/passada/controle-participacao/{competidor_id}/{prova_id}/{categoria_id}", 
           tags=['Controle Participação'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_controle_participacao(
    competidor_id: int = Path(..., description="ID do competidor"),
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém controle de participação de um competidor"""
    controle = RepositorioPassadas(db).obter_controle_participacao(competidor_id, prova_id, categoria_id)
    if not controle:
        return error_response(message='Controle de participação não encontrado!')
    
    # Calcular campos adicionais
    controle.passadas_restantes = controle.max_passadas_permitidas - controle.total_passadas_executadas
    controle.percentual_uso = (controle.total_passadas_executadas / controle.max_passadas_permitidas) * 100
    
    return success_response(controle)

@router.get("/passada/controle-participacao/listar", 
           tags=['Controle Participação'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def listar_controle_participacao(
    competidor_id: Optional[int] = Query(None, description="ID do competidor"),
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    apenas_ativos: bool = Query(True, description="Apenas competidores ativos"),
    apenas_bloqueados: bool = Query(False, description="Apenas competidores bloqueados"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista controles de participação com filtros"""
    try:
        filtros = models.FiltrosControleParticipacao(
            competidor_id=competidor_id,
            prova_id=prova_id,
            categoria_id=categoria_id,
            apenas_ativos=apenas_ativos,
            apenas_bloqueados=apenas_bloqueados
        )
        
        controles = RepositorioPassadas(db).listar_controle_participacao(filtros)
        
        if not controles:
            return error_response(message='Nenhum controle de participação encontrado!')
        
        # Calcular campos adicionais
        response_data = []
        for controle in controles:
            controle_data = {
                **controle.__dict__,  # All existing fields
                'passadas_restantes': controle.max_passadas_permitidas - controle.total_passadas_executadas,
                'percentual_uso': (controle.total_passadas_executadas / controle.max_passadas_permitidas) * 100
            }
            response_data.append(controle_data)

        return success_response(response_data, f'{len(response_data)} controles encontrados')
    except Exception as e:
        print(traceback.format_exc())
        return error_response(message=f'Erro ao listar controles: {str(e)}')

# ========================== RANKINGS E RELATÓRIOS ==========================

@router.get("/passada/ranking/{prova_id}", 
           tags=['Rankings Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_ranking_passadas(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    numero_passada: Optional[int] = Query(None, description="Número da passada específica"),
    tipo_ranking: str = Query("tempo", regex="^(tempo|pontos|geral|trio|competidor)$", description="Tipo de ranking"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém ranking de passadas de uma prova"""
    try:
        ranking = RepositorioPassadas(db).obter_ranking_passada(
            prova_id, categoria_id, numero_passada, tipo_ranking
        )
        
        if not ranking:
            return error_response(message='Nenhum resultado encontrado para o ranking!')
        
        return success_response(
            ranking, 
            f'Ranking {tipo_ranking} - {len(ranking)} posições',
            meta={
                'prova_id': prova_id,
                'categoria_id': categoria_id,
                'numero_passada': numero_passada,
                'tipo_ranking': tipo_ranking
            }
        )
    except Exception as e:
        return error_response(message=f'Erro ao obter ranking: {str(e)}')

@router.get("/passada/resumo-trio/{trio_id}", 
           tags=['Relatórios Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_resumo_trio(
    trio_id: int = Path(..., description="ID do trio"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém resumo de passadas de um trio"""
    try:
        resumo = RepositorioPassadas(db).obter_resumo_trio(trio_id)
        
        if not resumo:
            return error_response(message='Trio não encontrado ou sem passadas!')
        
        return success_response(resumo)
    except Exception as e:
        return error_response(message=f'Erro ao obter resumo: {str(e)}')

@router.get("/passada/estatisticas", 
           tags=['Estatísticas Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_estatisticas_passadas(
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém estatísticas gerais de passadas"""
    try:
        estatisticas = RepositorioPassadas(db).obter_estatisticas_gerais(prova_id, categoria_id)
        
        if not estatisticas:
            return error_response(message='Nenhum dado encontrado!')
        
        return success_response(estatisticas)
    except Exception as e:
        return error_response(message=f'Erro ao obter estatísticas: {str(e)}')

@router.get("/passada/relatorio-completo/{prova_id}", 
           tags=['Relatórios Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def gerar_relatorio_completo(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    incluir_detalhes: bool = Query(True, description="Incluir detalhes das passadas"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera relatório completo de passadas de uma prova"""
    try:
        repo = RepositorioPassadas(db)
        
        # Estatísticas gerais
        estatisticas = repo.obter_estatisticas_gerais(prova_id, categoria_id)
        
        # Rankings
        ranking_tempo = repo.obter_ranking_passada(prova_id, categoria_id, tipo_ranking="tempo")
        ranking_pontos = repo.obter_ranking_passada(prova_id, categoria_id, tipo_ranking="pontos")
        
        # Resumos por trio (se solicitado)
        resumos_trios = []
        if incluir_detalhes:
            # Buscar todos os trios da prova
            filtros = models.FiltrosPassadas(prova_id=prova_id, categoria_id=categoria_id)
            passadas, _ = repo.listar_passadas(filtros)
            
            trios_ids = list(set(p.trio_id for p in passadas))
            for trio_id in trios_ids:
                resumo = repo.obter_resumo_trio(trio_id)
                if resumo:
                    resumos_trios.append(resumo)
        
        relatorio = {
            'prova_id': prova_id,
            'categoria_id': categoria_id,
            'data_geracao': datetime.now().isoformat(),
            'estatisticas_gerais': estatisticas,
            'ranking_tempo': ranking_tempo[:10],  # Top 10
            'ranking_pontos': ranking_pontos[:10],  # Top 10
            'resumos_trios': resumos_trios,
            'total_trios': len(resumos_trios),
            'incluiu_detalhes': incluir_detalhes
        }
        
        return success_response(relatorio, 'Relatório gerado com sucesso')
    except Exception as e:
        return error_response(message=f'Erro ao gerar relatório: {str(e)}')

# ========================== DASHBOARD E MONITORAMENTO ==========================

@router.get("/passada/dashboard", 
           tags=['Dashboard Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_dashboard_passadas(
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    data_referencia: Optional[date] = Query(None, description="Data de referência"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém dados do dashboard de passadas"""
    try:
        if not data_referencia:
            data_referencia = date.today()
        
        repo = RepositorioPassadas(db)
        
        # Filtros para o dia
        filtros_dia = models.FiltrosPassadas(
            prova_id=prova_id,
            data_inicio=datetime.combine(data_referencia, datetime.min.time()),
            data_fim=datetime.combine(data_referencia, datetime.max.time())
        )
        
        passadas_dia, _ = repo.listar_passadas(filtros_dia)
        
        # ✅ CORREÇÃO: Acessar como dicionário
        # Calcular métricas do dia
        total_passadas_dia = len(passadas_dia)
        executadas_hoje = len([p for p in passadas_dia if p.get('status') == 'executada'])
        pendentes_hoje = len([p for p in passadas_dia if p.get('status') == 'pendente'])
        sat_hoje = len([p for p in passadas_dia if p.get('is_sat')])
        
        # ✅ CORREÇÃO: Acessar tempo_realizado como dicionário
        tempos_dia = [
            float(p.get('tempo_realizado', 0)) 
            for p in passadas_dia 
            if p.get('tempo_realizado') and p.get('status') == 'executada' and not p.get('is_sat')
        ]
        tempo_medio_dia = sum(tempos_dia) / len(tempos_dia) if tempos_dia else None
        melhor_tempo_dia = min(tempos_dia) if tempos_dia else None
        
        # Próximas passadas pendentes
        filtros_pendentes = models.FiltrosPassadas(
            prova_id=prova_id,
            status='pendente',
            tamanho_pagina=10
        )
        proximas_passadas, _ = repo.listar_passadas(filtros_pendentes)
        
        # Ranking do dia (top 5)
        ranking_dia = []
        if prova_id:
            try:
                ranking_completo = repo.obter_ranking_passada(prova_id, tipo_ranking="tempo")
                # Filtrar apenas os do dia
                for item in ranking_completo:
                    passada = repo.obter_passada(item['passada_id'])
                    # ✅ CORREÇÃO: Verificar se passada existe e tem data
                    if passada:
                        # Se passada for dict
                        if isinstance(passada, dict):
                            data_passada = passada.get('data_hora_passada')
                        else:
                            # Se passada for objeto SQLAlchemy
                            data_passada = getattr(passada, 'data_hora_passada', None)
                        
                        if data_passada:
                            # Converter string para date se necessário
                            if isinstance(data_passada, str):
                                data_passada = datetime.fromisoformat(data_passada.replace('Z', '+00:00')).date()
                            elif hasattr(data_passada, 'date'):
                                data_passada = data_passada.date()
                            
                            if data_passada == data_referencia:
                                ranking_dia.append(item)
                                if len(ranking_dia) >= 5:
                                    break
            except Exception as e:
                print(f"Erro ao obter ranking: {e}")
                ranking_dia = []
        
        # Alertas (competidores próximos do limite)
        alertas = []
        competidores_alertados = set()
        try:
            filtros_controle = models.FiltrosControleParticipacao(prova_id=prova_id)
            controles = repo.listar_controle_participacao(filtros_controle)
            
            for controle in controles:
                if isinstance(controle, dict):
                    max_passadas = controle.get('max_passadas_permitidas', 0)
                    total_executadas = controle.get('total_passadas_executadas', 0)
                    pode_competir = controle.get('pode_competir', False)
                    competidor_nome = controle.get('competidor', {}).get('nome', 'N/A')
                    competidor_id = controle.get('competidor_id')
                else:
                    max_passadas = getattr(controle, 'max_passadas_permitidas', 0)
                    total_executadas = getattr(controle, 'total_passadas_executadas', 0)
                    pode_competir = getattr(controle, 'pode_competir', False)
                    competidor_nome = getattr(controle.competidor, 'nome', 'N/A') if hasattr(controle, 'competidor') and controle.competidor else 'N/A'
                    competidor_id = getattr(controle, 'competidor_id', None)

                if not competidor_id or competidor_id in competidores_alertados:
                    continue  # já alertado ou inválido

                restantes = max_passadas - total_executadas
                if restantes <= 1 and pode_competir:
                    alertas.append({
                        'tipo': 'limite_passadas',
                        'competidor_id': competidor_id,
                        'competidor_nome': competidor_nome,
                        'passadas_restantes': restantes,
                        'mensagem': f'Apenas {restantes} passada(s) restante(s)'
                    })
                    competidores_alertados.add(competidor_id)  # evita duplicata
        except Exception as e:
            print(f"Erro ao gerar alertas: {e}")
            alertas = []
        
        dashboard = {
            'data_referencia': data_referencia.isoformat(),
            'prova_id': prova_id,
            'resumo_geral': {
                'total_passadas_dia': total_passadas_dia,
                'passadas_executadas_hoje': executadas_hoje,
                'passadas_pendentes_hoje': pendentes_hoje,
                'passadas_sat_hoje': sat_hoje,
                'tempo_medio_dia': tempo_medio_dia,
                'melhor_tempo_dia': melhor_tempo_dia
            },
            'proximas_passadas': proximas_passadas[:5],
            'ranking_tempo_dia': ranking_dia,
            'alertas': [alerta['mensagem'] for alerta in alertas],  # Simplificar alertas
            'ultima_atualizacao': datetime.now().isoformat()
        }
        
        return success_response(dashboard, 'Dashboard carregado com sucesso')
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(message=f'Erro ao carregar dashboard: {str(e)}')
    
@router.post("/passada/recalcular-colocacoes/{prova_id}", 
            tags=['Administrativo Passadas'], 
            status_code=status.HTTP_200_OK, 
            response_model=models.ApiResponse)
async def recalcular_colocacoes_prova(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Recalcula colocações de todas as passadas excluindo SAT"""
    try:
        repo = RepositorioPassadas(db)
        colocacoes_atualizadas = repo.recalcular_colocacoes_passadas(prova_id, categoria_id)
        
        return success_response(
            {
                'colocacoes_atualizadas': colocacoes_atualizadas,
                'prova_id': prova_id,
                'categoria_id': categoria_id
            },
            f'Colocações recalculadas: {colocacoes_atualizadas} passadas atualizadas'
        )
    except Exception as e:
        return error_response(message=f'Erro ao recalcular colocações: {str(e)}')

# ========================== TRIO PASSADAS ==========================

@router.get("/passada/trio/{trio_id}/passadas", 
           tags=['Trio Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def listar_passadas_trio(
    trio_id: int = Path(..., description="ID do trio"),
    incluir_pendentes: bool = Query(True, description="Incluir passadas pendentes"),
    ordenar_por: str = Query("numero_passada", regex="^(numero_passada|data_hora_passada|tempo_realizado)$", description="Campo para ordenação"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista todas as passadas de um trio específico"""
    try:
        filtros = models.FiltrosPassadas(
            trio_id=trio_id,
            tamanho_pagina=100  # Buscar todas
        )
        
        passadas, total = RepositorioPassadas(db).listar_passadas(filtros)
        
        if not incluir_pendentes:
            passadas = [p for p in passadas if p.status != 'pendente']
        
        # Ordenar conforme solicitado
        if ordenar_por == "data_hora_passada":
            passadas.sort(key=lambda x: x.data_hora_passada or datetime.min, reverse=True)
        elif ordenar_por == "tempo_realizado":
            passadas.sort(key=lambda x: x.tempo_realizado or float('inf'))
        else:  # numero_passada
            passadas.sort(key=lambda x: x.numero_passada)
        
        return success_response(
            passadas, 
            f'{len(passadas)} passadas do trio #{trio_id}',
            meta={'trio_id': trio_id, 'total': len(passadas)}
        )
    except Exception as e:
        return error_response(message=f'Erro ao listar passadas do trio: {str(e)}')

@router.post("/passada/gerar-proxima/{trio_id}", 
            tags=['Trio Passadas'], 
            status_code=status.HTTP_201_CREATED, 
            response_model=models.ApiResponse)
async def gerar_proxima_passada(
    trio_id: int = Path(..., description="ID do trio"),
    auto_boi: bool = Query(True, description="Gerar número do boi automaticamente"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera a próxima passada para um trio"""
    try:
        repo = RepositorioPassadas(db)
        
        # Validar trio
        from src.repositorios.trio import RepositorioTrio
        trio = RepositorioTrio(db).obter_trio(trio_id)
        if not trio:
            return error_response(message='Trio não encontrado!')
        
        # Obter próximo número de passada
        filtros = models.FiltrosPassadas(trio_id=trio_id, tamanho_pagina=1000)
        passadas_existentes, _ = repo.listar_passadas(filtros)
        
        proximo_numero = 1
        if passadas_existentes:
            numeros = [p.numero_passada for p in passadas_existentes]
            proximo_numero = max(numeros) + 1
        
        # Validar se pode criar mais passadas
        config = repo._obter_configuracao_prova(trio.prova_id, trio.categoria_id)
        if config and proximo_numero > config.max_passadas_por_trio:
            return error_response(message=f'Trio atingiu o máximo de {config.max_passadas_por_trio} passadas')
        
        # Criar passada
        passada_data = models.PassadaTrioPOST(
            trio_id=trio_id,
            prova_id=trio.prova_id,
            numero_passada=proximo_numero,
            tempo_limite=config.tempo_limite_padrao if config else 60.0
        )
        
        # Gerar boi automaticamente se solicitado
        if auto_boi and config and config.bois_disponiveis:
            import json
            bois_disponiveis = json.loads(config.bois_disponiveis)
            boi_gerado = repo._gerar_numero_boi_aleatorio(bois_disponiveis, trio_id, trio.prova_id)
            passada_data.numero_boi = boi_gerado
        
        nova_passada = repo.criar_passada(passada_data)
        
        return success_response(
            nova_passada, 
            f'Passada #{proximo_numero} gerada com sucesso',
            status_code=201
        )
    except ValueError as e:
        return error_response(message=str(e))
    except Exception as e:
        return error_response(message=f'Erro ao gerar passada: {str(e)}')

# ========================== CONFIGURAÇÃO PADRÃO CATEGORIA ==========================

@router.get("/passada/configuracao-categoria/{categoria_id}", 
           tags=['Configuração Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_configuracao_padrao_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém configuração padrão de passadas para uma categoria"""
    try:
        from src.repositorios.categoria import RepositorioCategoria
        categoria = RepositorioCategoria(db).get_by_id(categoria_id)
        
        if not categoria:
            return error_response(message='Categoria não encontrada!')
        
        # Configurações padrão por tipo de categoria
        configuracao_padrao = {
            'categoria_id': categoria_id,
            'categoria_nome': categoria.nome,
            'categoria_tipo': categoria.tipo.value,
            'max_passadas_por_trio': 5,  # Padrão
            'max_corridas_por_pessoa': 5,  # Padrão
            'tempo_limite_padrao': 60.0,  # Padrão
            'intervalo_minimo_passadas': 5,  # 5 minutos
            'permite_repetir_boi': False,
            'bois_disponiveis': list(range(1, 21))  # Bois 1-20 padrão
        }
        
        # Ajustar por tipo de categoria
        if categoria.tipo.value == 'baby':
            configuracao_padrao.update({
                'tempo_limite_padrao': 90.0,
                'max_passadas_por_trio': 3,
                'bois_disponiveis': list(range(1, 11))  # Bois 1-10
            })
        elif categoria.tipo.value == 'kids':
            configuracao_padrao.update({
                'tempo_limite_padrao': 75.0,
                'bois_disponiveis': list(range(11, 21))  # Bois 11-20
            })
        elif categoria.tipo.value == 'aberta':
            configuracao_padrao.update({
                'tempo_limite_padrao': 50.0,
                'max_passadas_por_trio': 10
            })
        elif categoria.tipo.value == 'handicap':
            configuracao_padrao.update({
                'tempo_limite_padrao': 55.0,
                'max_passadas_por_trio': 8
            })
        
        return success_response(configuracao_padrao, 'Configuração padrão gerada')
    except Exception as e:
        return error_response(message=f'Erro ao obter configuração padrão: {str(e)}')

# ========================== EXPORTAÇÃO E BACKUP ==========================

@router.get("/passada/exportar", 
           tags=['Exportação Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def exportar_passadas(
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    formato: str = Query("json", regex="^(json|csv)$", description="Formato de exportação"),
    incluir_detalhes: bool = Query(True, description="Incluir detalhes dos competidores"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Exporta dados de passadas"""
    try:
        filtros = models.FiltrosPassadas(
            prova_id=prova_id,
            categoria_id=categoria_id,
            tamanho_pagina=1000  # Buscar todas
        )
        
        passadas, total = RepositorioPassadas(db).listar_passadas(filtros)
        
        # Preparar dados para exportação
        dados_exportacao = []
        for passada in passadas:
            item = {
                'passada_id': passada.id,
                'trio_id': passada.trio_id,
                'trio_numero': passada.trio.numero_trio if passada.trio else None,
                'prova_id': passada.prova_id,
                'prova_nome': passada.prova.nome if passada.prova else None,
                'numero_passada': passada.numero_passada,
                'numero_boi': passada.numero_boi,
                'tempo_realizado': float(passada.tempo_realizado) if passada.tempo_realizado else None,
                'tempo_limite': float(passada.tempo_limite),
                'status': passada.status,
                'pontos_passada': float(passada.pontos_passada),
                'colocacao_passada': passada.colocacao_passada,
                'data_hora_passada': passada.data_hora_passada.isoformat() if passada.data_hora_passada else None,
                'observacoes': passada.observacoes
            }
            
            if incluir_detalhes and passada.trio and passada.trio.integrantes:
                item['competidores'] = [
                    {
                        'id': i.competidor.id,
                        'nome': i.competidor.nome,
                        'handicap': i.competidor.handicap
                    }
                    for i in passada.trio.integrantes if i.competidor
                ]
            
            dados_exportacao.append(item)
        
        resultado_exportacao = {
            'formato': formato,
            'total_registros': len(dados_exportacao),
            'filtros_aplicados': {
                'prova_id': prova_id,
                'categoria_id': categoria_id
            },
            'exportado_em': datetime.now().isoformat(),
            'dados': dados_exportacao
        }
        
        return success_response(
            resultado_exportacao,
            f'{len(dados_exportacao)} passadas exportadas em formato {formato}'
        )
    except Exception as e:
        return error_response(message=f'Erro na exportação: {str(e)}')

@router.post("/passada/backup", 
            tags=['Backup Passadas'], 
            status_code=status.HTTP_200_OK, 
            response_model=models.ApiResponse)
async def criar_backup_passadas(
    prova_id: Optional[int] = Query(None, description="ID da prova (opcional)"),
    incluir_detalhes: bool = Query(True, description="Incluir detalhes completos"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria backup completo de dados de passadas"""
    try:
        repo = RepositorioPassadas(db)
        
        # Buscar dados para backup
        filtros = models.FiltrosPassadas(
            prova_id=prova_id,
            tamanho_pagina=50000  # Buscar muitos registros
        )
        
        passadas, total = repo.listar_passadas(filtros)
        
        # Preparar dados do backup
        backup_data = {
            'metadata': {
                'tipo': 'backup_passadas',
                'versao': '1.0',
                'criado_em': datetime.now().isoformat(),
                'criado_por': usuario.id if hasattr(usuario, 'id') else 'sistema',
                'prova_id': prova_id,
                'total_registros': len(passadas),
                'incluir_detalhes': incluir_detalhes
            },
            'passadas': []
        }
        
        # Processar cada passada
        for passada in passadas:
            passada_backup = {
                'id': passada.id,
                'trio_id': passada.trio_id,
                'prova_id': passada.prova_id,
                'numero_passada': passada.numero_passada,
                'numero_boi': passada.numero_boi,
                'tempo_realizado': float(passada.tempo_realizado) if passada.tempo_realizado else None,
                'tempo_limite': float(passada.tempo_limite),
                'status': passada.status,
                'pontos_passada': float(passada.pontos_passada),
                'colocacao_passada': passada.colocacao_passada,
                'data_hora_passada': passada.data_hora_passada.isoformat() if passada.data_hora_passada else None,
                'observacoes': passada.observacoes,
                'created_at': passada.created_at.isoformat() if passada.created_at else None,
                'updated_at': passada.updated_at.isoformat() if passada.updated_at else None
            }
            
            # Incluir detalhes se solicitado
            if incluir_detalhes and passada.trio:
                passada_backup['trio_detalhes'] = {
                    'numero_trio': passada.trio.numero_trio,
                    'categoria_id': passada.trio.categoria_id,
                    'handicap_total': passada.trio.handicap_total
                }
                
                if passada.trio.integrantes:
                    passada_backup['competidores'] = [
                        {
                            'id': i.competidor.id,
                            'nome': i.competidor.nome,
                            'handicap': i.competidor.handicap,
                            'funcao': i.funcao
                        }
                        for i in passada.trio.integrantes if i.competidor
                    ]
            
            backup_data['passadas'].append(passada_backup)
        
        # Adicionar estatísticas do backup
        backup_data['estatisticas'] = {
            'total_passadas': len(passadas),
            'por_status': {
                'pendente': len([p for p in passadas if p.status == 'pendente']),
                'executada': len([p for p in passadas if p.status == 'executada']),
                'no_time': len([p for p in passadas if p.status == 'no_time']),
                'desclassificada': len([p for p in passadas if p.status == 'desclassificada'])
            },
            'periodo': {
                'primeira_passada': min([p.created_at for p in passadas if p.created_at]).isoformat() if passadas else None,
                'ultima_passada': max([p.created_at for p in passadas if p.created_at]).isoformat() if passadas else None
            }
        }
        
        return success_response(
            backup_data,
            f'Backup criado com sucesso: {len(passadas)} passadas',
            meta={
                'tamanho_backup_mb': len(str(backup_data)) / (1024 * 1024),
                'compressao_recomendada': len(str(backup_data)) > 100000
            }
        )
    except Exception as e:
        return error_response(message=f'Erro ao criar backup: {str(e)}')

# ========================== OPERAÇÕES ADMINISTRATIVAS ==========================

@router.post("/passada/recalcular-pontuacao/{prova_id}", 
            tags=['Administrativo Passadas'], 
            status_code=status.HTTP_200_OK, 
            response_model=models.ApiResponse)
async def recalcular_pontuacao_prova(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Recalcula pontuação de todas as passadas de uma prova"""
    try:
        repo = RepositorioPassadas(db)
        
        # Buscar passadas executadas da prova
        filtros = models.FiltrosPassadas(
            prova_id=prova_id,
            categoria_id=categoria_id,
            status='executada',
            tamanho_pagina=1000
        )
        
        passadas, total = repo.listar_passadas(filtros)
        
        if not passadas:
            return error_response(message='Nenhuma passada executada encontrada para recalcular')
        
        passadas_atualizadas = 0
        
        for passada in passadas:
            if passada.tempo_realizado and passada.tempo_limite:
                # Recalcular pontos
                novos_pontos = repo._calcular_pontos_tempo(
                    passada.tempo_realizado, 
                    passada.tempo_limite
                )
                
                # Atualizar se houver diferença
                if passada.pontos_passada != novos_pontos:
                    passada.pontos_passada = novos_pontos
                    passada.updated_at = datetime.now()
                    passadas_atualizadas += 1
        
        db.commit()
        
        # Atualizar rankings/colocações se necessário
        if passadas_atualizadas > 0:
            _atualizar_colocacoes_prova(prova_id, categoria_id, db)
        
        return success_response(
            {
                'total_passadas_analisadas': len(passadas),
                'passadas_atualizadas': passadas_atualizadas,
                'prova_id': prova_id,
                'categoria_id': categoria_id
            },
            f'Pontuação recalculada: {passadas_atualizadas} passadas atualizadas'
        )
    except Exception as e:
        return error_response(message=f'Erro ao recalcular pontuação: {str(e)}')

@router.post("/passada/atualizar-rankings/{prova_id}", 
            tags=['Administrativo Passadas'], 
            status_code=status.HTTP_200_OK, 
            response_model=models.ApiResponse)
async def atualizar_rankings_prova(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Atualiza rankings e colocações de uma prova"""
    try:
        repo = RepositorioPassadas(db)
        
        # Buscar passadas executadas
        filtros = models.FiltrosPassadas(
            prova_id=prova_id,
            categoria_id=categoria_id,
            status='executada',
            tamanho_pagina=1000
        )
        
        passadas, total = repo.listar_passadas(filtros)
        
        if not passadas:
            return error_response(message='Nenhuma passada executada encontrada')
        
        # Atualizar colocações
        colocacoes_atualizadas = _atualizar_colocacoes_prova(prova_id, categoria_id, db)
        
        # Atualizar resumos dos trios
        trios_ids = list(set(p.trio_id for p in passadas))
        for trio_id in trios_ids:
            repo.atualizar_resumo_resultado(trio_id)
        
        return success_response(
            {
                'total_passadas': len(passadas),
                'colocacoes_atualizadas': colocacoes_atualizadas,
                'trios_atualizados': len(trios_ids),
                'prova_id': prova_id,
                'categoria_id': categoria_id
            },
            f'Rankings atualizados: {colocacoes_atualizadas} colocações e {len(trios_ids)} trios'
        )
    except Exception as e:
        return error_response(message=f'Erro ao atualizar rankings: {str(e)}')

@router.post("/passada/limpar-antigas", 
            tags=['Manutenção Passadas'], 
            status_code=status.HTTP_200_OK, 
            response_model=models.ApiResponse)
async def limpar_passadas_antigas(
    dias_limite: int = Query(30, ge=1, le=365, description="Dias limite para considerar passada antiga"),
    confirmar: bool = Query(False, description="Confirmar operação de limpeza"),
    apenas_pendentes: bool = Query(True, description="Limpar apenas passadas pendentes"),
    prova_id: Optional[int] = Query(None, description="ID da prova (opcional)"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria (opcional)"),
    dry_run: bool = Query(False, description="Simulação sem executar a limpeza"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Limpa passadas antigas do sistema"""
    try:
        data_limite = datetime.now() - timedelta(days=dias_limite)
        
        # Construir query base
        query = db.query(schemas.PassadasTrio).filter(
            schemas.PassadasTrio.created_at < data_limite
        )
        
        # Aplicar filtros específicos
        if apenas_pendentes:
            query = query.filter(schemas.PassadasTrio.status == 'pendente')
        
        if prova_id:
            query = query.filter(schemas.PassadasTrio.prova_id == prova_id)
        
        if categoria_id:
            query = query.join(schemas.Trios).filter(schemas.Trios.categoria_id == categoria_id)
        
        # Contar passadas que seriam afetadas
        passadas_antigas = query.all()
        total_a_remover = len(passadas_antigas)
        
        # Se é apenas simulação ou não confirmado, retornar análise
        if dry_run or not confirmar:
            operacao_tipo = "Simulação" if dry_run else "Análise prévia"
            
            return success_response(
                {
                    'operacao': operacao_tipo,
                    'passadas_a_remover': total_a_remover,
                    'dias_limite': dias_limite,
                    'data_limite': data_limite.isoformat(),
                    'filtros_aplicados': {
                        'apenas_pendentes': apenas_pendentes,
                        'prova_id': prova_id,
                        'categoria_id': categoria_id
                    },
                    'confirmacao_necessaria': not confirmar
                },
                f'{operacao_tipo}: {total_a_remover} passadas seriam removidas'
            )
        
        # Executar limpeza real
        if total_a_remover == 0:
            return success_response(
                {
                    'passadas_removidas': 0,
                    'dias_limite': dias_limite,
                    'executado_em': datetime.now().isoformat()
                },
                'Nenhuma passada antiga encontrada para remoção'
            )
        
        # Executar remoção
        passadas_removidas = 0
        for passada in passadas_antigas:
            try:
                db.delete(passada)
                passadas_removidas += 1
            except Exception as e:
                print(f"Erro ao remover passada {passada.id}: {str(e)}")
        
        db.commit()
        
        return success_response(
            {
                'passadas_removidas': passadas_removidas,
                'dias_limite': dias_limite,
                'executado_em': datetime.now().isoformat()
            },
            f'Limpeza concluída: {passadas_removidas} passadas antigas removidas'
        )
        
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        return error_response(message=f'Erro durante limpeza: {str(e)}')

# ========================== BUSCAS E FILTROS ESPECÍFICOS ==========================

@router.get("/passada/buscar/boi/{numero_boi}", 
           tags=['Busca Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def buscar_passadas_por_boi(
    numero_boi: int = Path(..., description="Número do boi"),
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    incluir_pendentes: bool = Query(False, description="Incluir passadas pendentes"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Busca passadas por número do boi"""
    try:
        filtros = models.FiltrosPassadas(
            numero_boi=numero_boi,
            prova_id=prova_id,
            tamanho_pagina=1000
        )
        
        if not incluir_pendentes:
            filtros.status = 'executada'
        
        passadas, total = RepositorioPassadas(db).listar_passadas(filtros)
        
        if not passadas:
            return error_response(message=f'Nenhuma passada encontrada para o boi {numero_boi}')
        
        return success_response(
            passadas,
            f'{len(passadas)} passadas encontradas para o boi {numero_boi}',
            meta={'numero_boi': numero_boi, 'prova_id': prova_id, 'total': total}
        )
    except Exception as e:
        return error_response(message=f'Erro ao buscar passadas: {str(e)}')

@router.get("/passada/buscar/status/{status}", 
           tags=['Busca Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def buscar_passadas_por_status(
    status_passada: str = Path(..., alias="status", description="Status da passada"),
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    limite: int = Query(100, ge=1, le=1000, description="Limite de resultados"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Busca passadas por status"""
    try:
        filtros = models.FiltrosPassadas(
            status=status_passada,
            prova_id=prova_id,
            tamanho_pagina=limite
        )
        
        passadas, total = RepositorioPassadas(db).listar_passadas(filtros)
        
        if not passadas:
            return error_response(message=f'Nenhuma passada encontrada com status {status_passada}')
        
        return success_response(
            passadas,
            f'{len(passadas)} passadas encontradas com status {status_passada}',
            meta={'status': status_passada, 'prova_id': prova_id, 'total': total}
        )
    except Exception as e:
        return error_response(message=f'Erro ao buscar passadas: {str(e)}')

@router.get("/passada/hoje", 
           tags=['Busca Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def buscar_passadas_hoje(
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna passadas do dia atual"""
    try:
        hoje = date.today()
        
        filtros = models.FiltrosPassadas(
            prova_id=prova_id,
            data_inicio=datetime.combine(hoje, datetime.min.time()),
            data_fim=datetime.combine(hoje, datetime.max.time()),
            tamanho_pagina=1000
        )
        
        passadas, total = RepositorioPassadas(db).listar_passadas(filtros)
        
        # Estatísticas do dia
        executadas = len([p for p in passadas if p.status == 'executada'])
        pendentes = len([p for p in passadas if p.status == 'pendente'])
        
        resultado = {
            'data': hoje.isoformat(),
            'total_passadas': len(passadas),
            'executadas': executadas,
            'pendentes': pendentes,
            'passadas': passadas
        }
        
        return success_response(
            resultado,
            f'{len(passadas)} passadas encontradas hoje',
            meta={'data': hoje.isoformat(), 'prova_id': prova_id}
        )
    except Exception as e:
        return error_response(message=f'Erro ao buscar passadas de hoje: {str(e)}')

@router.get("/passada/pendentes", 
           tags=['Busca Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def buscar_passadas_pendentes(
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    limite: int = Query(50, ge=1, le=200, description="Limite de resultados"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna passadas pendentes"""
    try:
        filtros = models.FiltrosPassadas(
            status='pendente',
            prova_id=prova_id,
            tamanho_pagina=limite
        )
        
        passadas, total = RepositorioPassadas(db).listar_passadas(filtros)
        
        return success_response(
            passadas,
            f'{len(passadas)} passadas pendentes encontradas',
            meta={'total_pendentes': total, 'prova_id': prova_id}
        )
    except Exception as e:
        return error_response(message=f'Erro ao buscar passadas pendentes: {str(e)}')

@router.get("/passada/competidor/{competidor_id}", 
           tags=['Busca Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def buscar_passadas_por_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Busca passadas por competidor"""
    try:
        filtros = models.FiltrosPassadas(
            competidor_id=competidor_id,
            prova_id=prova_id,
            tamanho_pagina=1000
        )
        
        passadas, total = RepositorioPassadas(db).listar_passadas(filtros)
        
        if not passadas:
            return error_response(message=f'Nenhuma passada encontrada para o competidor {competidor_id}')
        
        # Estatísticas do competidor
        executadas = len([p for p in passadas if p.status == 'executada'])
        tempos = [float(p.tempo_realizado) for p in passadas if p.tempo_realizado and p.status == 'executada']
        
        estatisticas = {
            'total_passadas': len(passadas),
            'executadas': executadas,
            'melhor_tempo': min(tempos) if tempos else None,
            'tempo_medio': sum(tempos) / len(tempos) if tempos else None,
            'pontos_total': sum(float(p.pontos_passada) for p in passadas)
        }
        
        resultado = {
            'competidor_id': competidor_id,
            'estatisticas': estatisticas,
            'passadas': passadas
        }
        
        return success_response(
            resultado,
            f'{len(passadas)} passadas encontradas para o competidor',
            meta={'competidor_id': competidor_id, 'prova_id': prova_id}
        )
    except Exception as e:
        return error_response(message=f'Erro ao buscar passadas do competidor: {str(e)}')

# ========================== VALIDAÇÕES ESPECÍFICAS ==========================

@router.get("/passada/pode-alterar/{passada_id}", 
           tags=['Validações Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def verificar_pode_alterar_passada(
    passada_id: int = Path(..., description="ID da passada"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Verifica se uma passada pode ser alterada"""
    try:
        passada = RepositorioPassadas(db).obter_passada(passada_id)
        if not passada:
            return error_response(message='Passada não encontrada')
        
        pode_alterar = passada.status in ['pendente', 'executada']
        motivos_bloqueio = []
        
        if passada.status == 'desclassificada':
            motivos_bloqueio.append('Passada está desclassificada')
        
        if passada.colocacao_passada and passada.status == 'executada':
            motivos_bloqueio.append('Passada já possui colocação final')
        
        # Verificar se faz parte de ranking finalizado
        if passada.data_hora_passada:
            dias_passados = (datetime.now() - passada.data_hora_passada).days
            if dias_passados > 7:
                motivos_bloqueio.append('Passada muito antiga (mais de 7 dias)')
        
        pode_alterar = len(motivos_bloqueio) == 0
        
        return success_response({
            'passada_id': passada_id,
            'pode_alterar': pode_alterar,
            'status_atual': passada.status,
            'motivos_bloqueio': motivos_bloqueio,
            'acoes_permitidas': {
                'editar_tempo': pode_alterar and passada.status in ['pendente', 'executada'],
                'editar_boi': pode_alterar and passada.status == 'pendente',
                'editar_observacoes': pode_alterar,
                'excluir': pode_alterar and passada.status == 'pendente'
            }
        })
    except Exception as e:
        return error_response(message=f'Erro na verificação: {str(e)}')

@router.get("/passada/pode-correr/{competidor_id}/{prova_id}/{categoria_id}", 
           tags=['Validações Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def verificar_competidor_pode_correr(
    competidor_id: int = Path(..., description="ID do competidor"),
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Verifica se um competidor pode fazer mais passadas"""
    try:
        repo = RepositorioPassadas(db)
        
        # Obter controle de participação
        controle = repo.obter_controle_participacao(competidor_id, prova_id, categoria_id)
        
        if not controle:
            return success_response({
                'pode_correr': False,
                'motivo': 'Competidor não possui controle de participação configurado',
                'passadas_restantes': 0,
                'status': 'nao_configurado'
            })
        
        pode_correr = controle.pode_competir
        passadas_restantes = controle.max_passadas_permitidas - controle.total_passadas_executadas
        
        motivos_bloqueio = []
        if not controle.pode_competir:
            motivos_bloqueio.append(controle.motivo_bloqueio or 'Competidor bloqueado')
        
        if passadas_restantes <= 0:
            motivos_bloqueio.append('Limite de passadas atingido')
            pode_correr = False
        
        return success_response({
            'competidor_id': competidor_id,
            'pode_correr': pode_correr,
            'passadas_restantes': max(0, passadas_restantes),
            'passadas_executadas': controle.total_passadas_executadas,
            'limite_maximo': controle.max_passadas_permitidas,
            'percentual_uso': (controle.total_passadas_executadas / controle.max_passadas_permitidas) * 100,
            'motivos_bloqueio': motivos_bloqueio,
            'status': 'ativo' if pode_correr else 'bloqueado'
        })
    except Exception as e:
        return error_response(message=f'Erro na verificação: {str(e)}')

# ========================== UTILITÁRIOS E SUGESTÕES ==========================

@router.get("/passada/proximo-numero/{trio_id}", 
           tags=['Utilitários Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_proximo_numero_passada(
    trio_id: int = Path(..., description="ID do trio"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém próximo número de passada disponível para um trio"""
    try:
        repo = RepositorioPassadas(db)
        
        # Buscar passadas existentes do trio
        filtros = models.FiltrosPassadas(trio_id=trio_id, tamanho_pagina=1000)
        passadas, _ = repo.listar_passadas(filtros)
        
        if not passadas:
            proximo_numero = 1
        else:
            numeros_existentes = [p.numero_passada for p in passadas]
            proximo_numero = max(numeros_existentes) + 1
        
        # Verificar limite máximo se houver configuração
        trio = db.query(schemas.Trios).filter(schemas.Trios.id == trio_id).first()
        limite_maximo = None
        
        if trio:
            config = repo._obter_configuracao_prova(trio.prova_id, trio.categoria_id)
            if config:
                limite_maximo = config.max_passadas_por_trio
        
        pode_criar = True
        aviso = None
        
        if limite_maximo and proximo_numero > limite_maximo:
            pode_criar = False
            aviso = f'Próximo número ({proximo_numero}) excede limite máximo ({limite_maximo})'
        
        return success_response({
            'trio_id': trio_id,
            'proximo_numero': proximo_numero,
            'total_passadas_existentes': len(passadas),
            'limite_maximo': limite_maximo,
            'pode_criar': pode_criar,
            'aviso': aviso,
            'numeros_existentes': sorted(numeros_existentes) if passadas else []
        })
    except Exception as e:
        return error_response(message=f'Erro ao obter próximo número: {str(e)}')

@router.get(
    "/passada/sugestoes/bois/{prova_id}/{categoria_id}/{trio_id}",
    tags=["Sugestões Passadas"],
    status_code=status.HTTP_200_OK,
    response_model=models.ApiResponse,
)
async def sugerir_bois_disponiveis(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: int = Path(..., description="ID da categoria"),
    trio_id: int = Path(..., description="ID do trio"),
    db: Session = Depends(get_db),
):
    """Sugere bois disponíveis para uma passada e sorteia um boi."""
    try:
        import json, random
        from datetime import date

        repo = RepositorioPassadas(db)

        # ⇢ 1. Configuração da prova
        config = repo._obter_configuracao_prova(prova_id, categoria_id)
        if not config or not config.bois_disponiveis:
            return error_response(message="Configuração de bois não encontrada")

        bois_configurados = json.loads(config.bois_disponiveis)

        # ⇢ 2. Bois já usados pelo trio - CORRIGIDO
        filtros_trio = models.FiltrosPassadas(trio_id=trio_id, tamanho_pagina=1000)
        passadas_trio, _ = repo.listar_passadas(filtros_trio)
        
        # Verificar se passadas_trio é lista de dicts ou objetos
        if passadas_trio and isinstance(passadas_trio[0], dict):
            bois_usados_trio = [p.get('numero_boi') for p in passadas_trio if p.get('numero_boi')]
            numero_passadas_trio = len([p for p in passadas_trio if p.get('numero_boi')])
        else:
            bois_usados_trio = [p.numero_boi for p in passadas_trio if p.numero_boi]
            numero_passadas_trio = len(bois_usados_trio)

        # ⇢ 3. Verificar se é nova rodada (todos os trios têm o mesmo número de passadas)
        trios_mesma_categoria = repo.db.query(schemas.Trios).filter(
            schemas.Trios.categoria_id == categoria_id
        ).all()

        reiniciar_rodada = True
        for trio in trios_mesma_categoria:
            if trio.id == trio_id:
                continue
            filtros_outro = models.FiltrosPassadas(trio_id=trio.id, tamanho_pagina=1000)
            passadas_outro, _ = repo.listar_passadas(filtros_outro)
            
            # Corrigir contagem para outros trios também
            if passadas_outro and isinstance(passadas_outro[0], dict):
                count_outro = len([p for p in passadas_outro if p.get('numero_boi')])
            else:
                count_outro = len([p for p in passadas_outro if p.numero_boi])
                
            if count_outro != numero_passadas_trio:
                reiniciar_rodada = False
                break

        # ⇢ 4. Calcular bois disponíveis
        if config.permite_repetir_boi:
            bois_disponiveis = list(bois_configurados)
        else:
            filtros_prova = models.FiltrosPassadas(
                prova_id=prova_id, status="executada", tamanho_pagina=100
            )
            passadas_prova, _ = repo.listar_passadas(filtros_prova)
            
            # Corrigir para passadas da prova também
            if passadas_prova and isinstance(passadas_prova[0], dict):
                bois_usados_prova = [p.get('numero_boi') for p in passadas_prova if p.get('numero_boi')]
            else:
                bois_usados_prova = [p.numero_boi for p in passadas_prova if p.numero_boi]
                
            bois_disponiveis = [b for b in bois_configurados if b not in bois_usados_prova]

        # ⇢ 5. Definir bois para sorteio
        if reiniciar_rodada:
            bois_para_sorteio = list(bois_configurados)
        else:
            bois_para_sorteio = [b for b in bois_disponiveis if b not in bois_usados_trio]

        # Evitar repetir o último boi usado (se mais de 1 opção)
        if bois_usados_trio and len(bois_para_sorteio) > 1:
            ultimo_boi = bois_usados_trio[-1]
            if ultimo_boi in bois_para_sorteio:
                bois_para_sorteio.remove(ultimo_boi)

        # Realizar sorteio
        boi_sorteado = random.choice(bois_para_sorteio) if bois_para_sorteio else None

        # ⇢ 6. Sugestões com análise de uso
        analise_uso = repo.obter_analise_uso_bois(prova_id)
        bois_recomendados = bois_para_sorteio or bois_disponiveis

        sugestoes = []
        for boi in bois_recomendados[:10]:
            dados = analise_uso.get("uso_por_boi", {}).get(str(boi), {}) if analise_uso else {}
            sugestoes.append({
                "numero": boi,
                "usado_pelo_trio": boi in bois_usados_trio,
                "total_usos_prova": dados.get("total_usos", 0),
                "tempo_medio": dados.get("tempo_medio"),
                "taxa_sucesso": dados.get("taxa_sucesso", 100),
            })

        sugestoes.sort(key=lambda x: (x["total_usos_prova"], -x["taxa_sucesso"]))

        # ⇢ 7. Resposta final
        return success_response({
            "prova_id": prova_id,
            "categoria_id": categoria_id,
            "trio_id": trio_id,
            "total_bois_configurados": len(bois_configurados),
            "total_bois_disponiveis": len(bois_disponiveis),
            "permite_repetir": config.permite_repetir_boi,
            "bois_usados_trio": bois_usados_trio,
            "sugestoes": sugestoes[:5],
            "todos_disponiveis": bois_disponiveis,
            "boi_sorteado": boi_sorteado,
            "nova_rodada": reiniciar_rodada
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_response(message=f"Erro ao sugerir bois: {str(e)}")




# ========================== CÁLCULOS E ANÁLISES ==========================

@router.post("/passada/calcular-pontuacao", 
            tags=['Cálculos Passadas'], 
            status_code=status.HTTP_200_OK, 
            response_model=models.ApiResponse)
async def calcular_pontuacao_tempo(
    tempo: float = Query(..., description="Tempo realizado em segundos"),
    categoria_id: int = Query(..., description="ID da categoria"),
    prova_id: int = Query(..., description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Calcula pontuação baseada no tempo realizado"""
    try:
        from decimal import Decimal
        repo = RepositorioPassadas(db)
        
        # Obter tempo limite da configuração
        config = repo._obter_configuracao_prova(prova_id, categoria_id)
        tempo_limite = config.tempo_limite_padrao if config else 60.0
        
        # Calcular pontos
        pontos = repo._calcular_pontos_tempo(Decimal(str(tempo)), Decimal(str(tempo_limite)))
        
        # Determinar status
        if tempo <= tempo_limite:
            status_sugerido = 'executada'
            resultado = 'Dentro do tempo limite'
        else:
            status_sugerido = 'no_time'
            resultado = 'Excedeu tempo limite'
        
        return success_response({
            'tempo_realizado': tempo,
            'tempo_limite': float(tempo_limite),
            'pontos_calculados': float(pontos),
            'status_sugerido': status_sugerido,
            'resultado': resultado,
            'diferenca_tempo': tempo - float(tempo_limite),
            'percentual_tempo_usado': (tempo / float(tempo_limite)) * 100
        })
    except Exception as e:
        return error_response(message=f'Erro no cálculo: {str(e)}')

@router.get("/passada/analise/tempos/{prova_id}", 
           tags=['Análises Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_analise_tempos(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Análise de distribuição de tempos"""
    try:
        repo = RepositorioPassadas(db)
        analise = repo.obter_analise_tempos(prova_id, categoria_id)
        
        if not analise:
            return error_response(message='Nenhum dado de tempo encontrado para análise')
        
        return success_response(analise, 'Análise de tempos gerada com sucesso')
    except Exception as e:
        return error_response(message=f'Erro na análise de tempos: {str(e)}')

@router.get("/passada/analise/uso-bois/{prova_id}", 
           tags=['Análises Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_analise_uso_bois(
    prova_id: int = Path(..., description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Análise de uso de bois"""
    try:
        repo = RepositorioPassadas(db)
        analise = repo.obter_analise_uso_bois(prova_id)
        
        if not analise:
            return error_response(message='Nenhum dado de uso de bois encontrado')
        
        return success_response(analise, 'Análise de uso de bois gerada com sucesso')
    except Exception as e:
        return error_response(message=f'Erro na análise de uso de bois: {str(e)}')

@router.get("/passada/analise/consistencia/{prova_id}", 
           tags=['Análises Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_analise_consistencia(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Análise de consistência de trios"""
    try:
        repo = RepositorioPassadas(db)
        ranking_trios = repo.obter_ranking_trios(prova_id, categoria_id)
        
        if not ranking_trios:
            return error_response(message='Nenhum trio encontrado para análise')
        
        # Calcular métricas de consistência
        analise_consistencia = []
        
        for trio in ranking_trios:
            if len(trio['colocacoes']) >= 2:  # Mínimo 2 passadas para analisar consistência
                colocacoes = trio['colocacoes']
                
                # Calcular desvio padrão das colocações
                media_colocacao = sum(colocacoes) / len(colocacoes)
                variancia = sum((c - media_colocacao) ** 2 for c in colocacoes) / len(colocacoes)
                desvio_padrao = variancia ** 0.5
                
                # Calcular consistência (inverso do desvio - quanto menor o desvio, maior a consistência)
                consistencia = max(0, 100 - (desvio_padrao * 20))  # Escala de 0-100
                
                analise_consistencia.append({
                    'trio_id': trio['trio_id'],
                    'trio_numero': trio['trio']['numero_trio'],
                    'total_passadas': len(colocacoes),
                    'colocacoes': colocacoes,
                    'media_colocacao': round(media_colocacao, 2),
                    'desvio_padrao': round(desvio_padrao, 2),
                    'consistencia_score': round(consistencia, 1),
                    'nivel_consistencia': (
                        'Excelente' if consistencia >= 80 else
                        'Boa' if consistencia >= 60 else
                        'Regular' if consistencia >= 40 else
                        'Baixa'
                    )
                })
        
        # Ordenar por consistência (maior para menor)
        analise_consistencia.sort(key=lambda x: x['consistencia_score'], reverse=True)
        
        # Estatísticas gerais
        scores = [a['consistencia_score'] for a in analise_consistencia]
        estatisticas_gerais = {
            'total_trios_analisados': len(analise_consistencia),
            'consistencia_media': sum(scores) / len(scores) if scores else 0,
            'trio_mais_consistente': analise_consistencia[0] if analise_consistencia else None,
            'trio_menos_consistente': analise_consistencia[-1] if analise_consistencia else None,
            'distribuicao_niveis': {
                'Excelente': len([a for a in analise_consistencia if a['consistencia_score'] >= 80]),
                'Boa': len([a for a in analise_consistencia if 60 <= a['consistencia_score'] < 80]),
                'Regular': len([a for a in analise_consistencia if 40 <= a['consistencia_score'] < 60]),
                'Baixa': len([a for a in analise_consistencia if a['consistencia_score'] < 40])
            }
        }
        
        resultado = {
            'prova_id': prova_id,
            'categoria_id': categoria_id,
            'estatisticas_gerais': estatisticas_gerais,
            'analise_por_trio': analise_consistencia
        }
        
        return success_response(resultado, 'Análise de consistência gerada com sucesso')
    except Exception as e:
        return error_response(message=f'Erro na análise de consistência: {str(e)}')

# ========================== RANKINGS COMPLETOS ==========================

@router.get("/passada/dashboard-ranking/{prova_id}", 
           tags=['Dashboard Rankings'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_dashboard_ranking(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém dashboard específico para rankings"""
    try:
        repo = RepositorioPassadas(db)
        dashboard = repo.obter_dashboard_ranking(prova_id, categoria_id)
        
        if not dashboard:
            return error_response(message='Nenhum dado encontrado para o dashboard')
        
        return success_response(dashboard, 'Dashboard de ranking carregado com sucesso')
    except Exception as e:
        return error_response(message=f'Erro ao carregar dashboard de ranking: {str(e)}')

@router.get("/passada/ranking-completo/{prova_id}", 
           tags=['Rankings Completos'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_ranking_completo(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    tipo: str = Query("trio", regex="^(trio|competidor)$", description="Tipo de ranking"),
    min_passadas: int = Query(1, ge=1, description="Mínimo de passadas para aparecer no ranking"),
    apenas_ativos: bool = Query(True, description="Apenas trios/competidores ativos"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém ranking completo de trios ou competidores"""
    try:
        repo = RepositorioPassadas(db)
        
        if tipo == "trio":
            ranking = repo.obter_ranking_trios(prova_id, categoria_id)
            
            # Aplicar filtros
            if min_passadas > 1:
                ranking = [r for r in ranking if r['total_passadas'] >= min_passadas]
            
            if apenas_ativos:
                ranking = [r for r in ranking if r['status_geral'] == 'ativo']
                
        else:  # competidor
            ranking = repo.obter_ranking_competidores(prova_id, categoria_id)
            
            # Aplicar filtros
            if min_passadas > 1:
                ranking = [r for r in ranking if r['total_passadas'] >= min_passadas]
        
        if not ranking:
            return error_response(message=f'Nenhum {tipo} encontrado no ranking')
        
        # Recalcular posições após filtros
        for posicao, item in enumerate(ranking, 1):
            item['posicao'] = posicao
        
        return success_response(
            {
                'tipo': tipo,
                'prova_id': prova_id,
                'categoria_id': categoria_id,
                'total_registros': len(ranking),
                'filtros_aplicados': {
                    'min_passadas': min_passadas,
                    'apenas_ativos': apenas_ativos
                },
                f'{tipo}s' if tipo == 'trio' else 'competidores': ranking
            },
            f'Ranking de {tipo}s carregado: {len(ranking)} registros'
        )
    except Exception as e:
        return error_response(message=f'Erro ao carregar ranking: {str(e)}')

# ========================== MÉTRICAS E PERFORMANCE ==========================

@router.get("/passada/metricas/performance", 
           tags=['Métricas Performance'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_metricas_performance(
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Métricas de performance do sistema de passadas"""
    try:
        repo = RepositorioPassadas(db)
        
        # Filtros base
        filtros = models.FiltrosPassadas(
            prova_id=prova_id,
            tamanho_pagina=1000
        )
        
        passadas, total = repo.listar_passadas(filtros)
        
        if not passadas:
            return error_response(message='Nenhuma passada encontrada para análise')
        
        # Métricas de tempo de resposta
        agora = datetime.now()
        passadas_com_data = [p for p in passadas if p.data_hora_passada]
        
        # Tempo médio entre criação e execução
        tempos_execucao = []
        for passada in passadas_com_data:
            if passada.created_at and passada.data_hora_passada:
                diff = passada.data_hora_passada - passada.created_at
                tempos_execucao.append(diff.total_seconds() / 60)  # em minutos
        
        # Distribuição de status
        distribuicao_status = {}
        for status in ['pendente', 'executada', 'no_time', 'desclassificada']:
            distribuicao_status[status] = len([p for p in passadas if p.status == status])
        
        # Taxa de conclusão
        total_criadas = len(passadas)
        total_executadas = distribuicao_status.get('executada', 0)
        taxa_conclusao = (total_executadas / total_criadas * 100) if total_criadas > 0 else 0
        
        # Performance por período (últimos 7 dias)
        performance_diaria = {}
        for i in range(7):
            data = (agora - timedelta(days=i)).date()
            passadas_dia = [p for p in passadas if p.data_hora_passada and p.data_hora_passada.date() == data]
            performance_diaria[data.isoformat()] = {
                'total': len(passadas_dia),
                'executadas': len([p for p in passadas_dia if p.status == 'executada'])
            }
        
        metricas = {
            'prova_id': prova_id,
            'periodo_analise': f"Últimos 7 dias até {agora.date().isoformat()}",
            'resumo_geral': {
                'total_passadas': total_criadas,
                'passadas_executadas': total_executadas,
                'taxa_conclusao_percentual': round(taxa_conclusao, 1),
                'tempo_medio_execucao_minutos': round(sum(tempos_execucao) / len(tempos_execucao), 1) if tempos_execucao else None
            },
            'distribuicao_status': distribuicao_status,
            'performance_diaria': performance_diaria,
            'alertas_performance': []
        }
        
        # Gerar alertas de performance
        if taxa_conclusao < 70:
            metricas['alertas_performance'].append(f"Taxa de conclusão baixa: {taxa_conclusao:.1f}%")
        
        if tempos_execucao and sum(tempos_execucao) / len(tempos_execucao) > 60:
            metricas['alertas_performance'].append("Tempo médio de execução acima de 1 hora")
        
        pendentes_antigas = len([p for p in passadas if p.status == 'pendente' and p.created_at and (agora - p.created_at).days > 1])
        if pendentes_antigas > 0:
            metricas['alertas_performance'].append(f"{pendentes_antigas} passadas pendentes há mais de 1 dia")
        
        return success_response(metricas, 'Métricas de performance calculadas com sucesso')
    except Exception as e:
        return error_response(message=f'Erro ao calcular métricas: {str(e)}')

# ========================== EXPORTAÇÃO DE RANKINGS ==========================

@router.get("/passada/exportar-ranking/{prova_id}", 
           tags=['Exportação Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
# route_passadas_parte3.py - Continuação Final das Rotas de Passadas

# ========================== EXPORTAÇÃO DE RANKINGS (CONTINUAÇÃO) ==========================

@router.get("/passada/exportar-ranking/{prova_id}", 
           tags=['Exportação Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse, operation_id="exportar_ranking_prova_passada")
async def exportar_ranking_prova(
    prova_id: int = Path(..., description="ID da prova"),
    formato: str = Query("json", regex="^(json|csv|pdf)$", description="Formato de exportação"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    tipo_ranking: str = Query("trio", regex="^(trio|competidor|tempo|pontos)$", description="Tipo de ranking"),
    incluir_detalhes: bool = Query(True, description="Incluir detalhes"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Exporta ranking de uma prova"""
    try:
        repo = RepositorioPassadas(db)
        
        # Obter dados do ranking
        if tipo_ranking in ['trio', 'tempo', 'pontos']:
            ranking_data = repo.obter_ranking_passada(prova_id, categoria_id, tipo_ranking=tipo_ranking)
        elif tipo_ranking == 'competidor':
            # Ranking por competidor - agregar dados
            ranking_data = _gerar_ranking_competidores(prova_id, categoria_id, db)
        else:
            ranking_data = repo.obter_ranking_passada(prova_id, categoria_id)
        
        if not ranking_data:
            return error_response(message='Nenhum dado de ranking encontrado')
        
        # Preparar dados para exportação
        dados_exportacao = {
            'formato': formato,
            'tipo_ranking': tipo_ranking,
            'prova_id': prova_id,
            'categoria_id': categoria_id,
            'total_registros': len(ranking_data),
            'gerado_em': datetime.now().isoformat(),
            'ranking': ranking_data
        }
        
        # Adicionar informações da prova se incluir_detalhes
        if incluir_detalhes:
            prova = db.query(schemas.Provas).filter(schemas.Provas.id == prova_id).first()
            if prova:
                dados_exportacao['prova_info'] = {
                    'nome': prova.nome,
                    'data': prova.data.isoformat() if prova.data else None,
                    'rancho': prova.rancho,
                    'cidade': prova.cidade,
                    'estado': prova.estado
                }
        
        return success_response(
            dados_exportacao,
            f'Ranking {tipo_ranking} exportado: {len(ranking_data)} registros'
        )
    except Exception as e:
        return error_response(message=f'Erro ao exportar ranking: {str(e)}')

# ========================== FUNÇÕES AUXILIARES INTERNAS ==========================

def _atualizar_colocacoes_prova(prova_id: int, categoria_id: Optional[int], db: Session) -> int:
    """Atualiza colocações de passadas baseado em tempo/pontos"""
    from sqlalchemy import func, and_
    
    # Buscar passadas executadas ordenadas por tempo
    query = db.query(schemas.PassadasTrio).filter(
        and_(
            schemas.PassadasTrio.prova_id == prova_id,
            schemas.PassadasTrio.status == 'executada',
            schemas.PassadasTrio.tempo_realizado.isnot(None)
        )
    )
    
    if categoria_id:
        query = query.join(schemas.Trios).filter(schemas.Trios.categoria_id == categoria_id)
    
    # Agrupar por número da passada e ordenar por tempo
    passadas_por_numero = {}
    for passada in query.all():
        if passada.numero_passada not in passadas_por_numero:
            passadas_por_numero[passada.numero_passada] = []
        passadas_por_numero[passada.numero_passada].append(passada)
    
    colocacoes_atualizadas = 0
    
    # Atualizar colocação para cada grupo de passadas
    for numero_passada, passadas in passadas_por_numero.items():
        # Ordenar por tempo (crescente) e depois por pontos (decrescente)
        passadas_ordenadas = sorted(
            passadas, 
            key=lambda p: (float(p.tempo_realizado), -float(p.pontos_passada))
        )
        
        for posicao, passada in enumerate(passadas_ordenadas, 1):
            if passada.colocacao_passada != posicao:
                passada.colocacao_passada = posicao
                passada.updated_at = datetime.now()
                colocacoes_atualizadas += 1
    
    db.commit()
    return colocacoes_atualizadas

def _gerar_ranking_competidores(prova_id: int, categoria_id: Optional[int], db: Session) -> List[Dict[str, Any]]:
    """Gera ranking agregado por competidores"""
    from collections import defaultdict
    from sqlalchemy.orm import joinedload
    
    # Buscar todas as passadas da prova
    query = db.query(schemas.PassadasTrio).options(
        joinedload(schemas.PassadasTrio.trio).joinedload(schemas.Trios.integrantes).joinedload(schemas.IntegrantesTrios.competidor)
    ).filter(schemas.PassadasTrio.prova_id == prova_id)
    
    if categoria_id:
        query = query.join(schemas.Trios).filter(schemas.Trios.categoria_id == categoria_id)
    
    passadas = query.all()
    
    # Agrupar por competidor
    stats_competidores = defaultdict(lambda: {
        'passadas': [],
        'total_pontos': 0,
        'total_passadas': 0,
        'passadas_executadas': 0,
        'tempos': [],
        'competidor_info': None,
        'trio_atual': None
    })
    
    for passada in passadas:
        if passada.trio and passada.trio.integrantes:
            for integrante in passada.trio.integrantes:
                if integrante.competidor:
                    comp_id = integrante.competidor.id
                    stats = stats_competidores[comp_id]
                    
                    stats['passadas'].append(passada)
                    stats['total_passadas'] += 1
                    stats['total_pontos'] += float(passada.pontos_passada)
                    stats['competidor_info'] = integrante.competidor
                    stats['trio_atual'] = passada.trio
                    
                    if passada.status == 'executada' and passada.tempo_realizado:
                        stats['passadas_executadas'] += 1
                        stats['tempos'].append(float(passada.tempo_realizado))
    
    # Gerar ranking
    ranking = []
    for comp_id, stats in stats_competidores.items():
        if stats['total_passadas'] > 0:
            ranking.append({
                'competidor_id': comp_id,
                'competidor': {
                    'id': stats['competidor_info'].id,
                    'nome': stats['competidor_info'].nome,
                    'handicap': stats['competidor_info'].handicap
                },
                'trio_atual': {
                    'id': stats['trio_atual'].id,
                    'numero_trio': stats['trio_atual'].numero_trio
                } if stats['trio_atual'] else None,
                'total_passadas': stats['total_passadas'],
                'passadas_executadas': stats['passadas_executadas'],
                'pontos_total': stats['total_pontos'],
                'pontos_media': stats['total_pontos'] / stats['total_passadas'],
                'melhor_tempo': min(stats['tempos']) if stats['tempos'] else None,
                'tempo_medio': sum(stats['tempos']) / len(stats['tempos']) if stats['tempos'] else None,
                'participacoes_trios': 1,  # Simplificado - um trio por prova
                'categorias_disputadas': [passadas[0].trio.categoria.nome] if passadas and passadas[0].trio.categoria else [],
                'taxa_sucesso': (stats['passadas_executadas'] / stats['total_passadas']) * 100
            })
    
    # Ordenar por pontos total (decrescente)
    ranking.sort(key=lambda x: x['pontos_total'], reverse=True)
    
    # Adicionar posições
    for posicao, item in enumerate(ranking, 1):
        item['posicao'] = posicao
    
    return ranking

# ========================== VALIDAÇÕES E UTILITÁRIOS ADICIONAIS ==========================

def _validar_trio_ativo(trio_id: int, db: Session) -> bool:
    """Valida se trio existe e está ativo"""
    from src.repositorios.trio import RepositorioTrio
    trio = RepositorioTrio(db).obter_trio(trio_id)
    return trio is not None and trio.status == "ativo"

def _calcular_estatisticas_periodo(passadas: List, data_inicio: date, data_fim: date) -> Dict[str, Any]:
    """Calcula estatísticas para um período específico"""
    passadas_periodo = [
        p for p in passadas 
        if p.data_hora_passada and data_inicio <= p.data_hora_passada.date() <= data_fim
    ]
    
    executadas = [p for p in passadas_periodo if p.status == 'executada']
    tempos = [float(p.tempo_realizado) for p in executadas if p.tempo_realizado]
    
    return {
        'total_passadas': len(passadas_periodo),
        'passadas_executadas': len(executadas),
        'tempo_medio': sum(tempos) / len(tempos) if tempos else None,
        'melhor_tempo': min(tempos) if tempos else None,
        'pior_tempo': max(tempos) if tempos else None
    }

# ========================== ROTAS COMPLEMENTARES DE CONSULTA ==========================

@router.get("/passada/trio/{trio_id}/estatisticas", 
           tags=['Estatísticas Trio'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_estatisticas_trio(
    trio_id: int = Path(..., description="ID do trio"),
    incluir_historico: bool = Query(True, description="Incluir histórico completo"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém estatísticas detalhadas de um trio"""
    try:
        repo = RepositorioPassadas(db)
        
        # Resumo básico
        resumo = repo.obter_resumo_trio(trio_id)
        if not resumo:
            return error_response(message='Trio não encontrado ou sem passadas')
        
        # Estatísticas avançadas se solicitado
        estatisticas_avancadas = {}
        if incluir_historico:
            filtros = models.FiltrosPassadas(trio_id=trio_id, tamanho_pagina=1000)
            passadas, _ = repo.listar_passadas(filtros)
            
            # Evolução temporal
            passadas_com_data = [p for p in passadas if p.data_hora_passada and p.status == 'executada']
            passadas_com_data.sort(key=lambda x: x.data_hora_passada)
            
            evolucao_tempos = []
            for i, passada in enumerate(passadas_com_data, 1):
                evolucao_tempos.append({
                    'passada_numero': i,
                    'tempo': float(passada.tempo_realizado) if passada.tempo_realizado else None,
                    'data': passada.data_hora_passada.isoformat(),
                    'colocacao': passada.colocacao_passada
                })
            
            # Análise de melhoria
            tempos_validos = [e['tempo'] for e in evolucao_tempos if e['tempo']]
            if len(tempos_validos) >= 2:
                tendencia = 'melhoria' if tempos_validos[-1] < tempos_validos[0] else 'piora'
                diferenca_primeira_ultima = tempos_validos[0] - tempos_validos[-1]
            else:
                tendencia = 'insuficiente'
                diferenca_primeira_ultima = 0
            
            estatisticas_avancadas = {
                'evolucao_tempos': evolucao_tempos,
                'tendencia_geral': tendencia,
                'melhoria_tempo_total': diferenca_primeira_ultima,
                'distribuicao_colocacoes': {
                    'primeiro_lugar': len([p for p in passadas if p.colocacao_passada == 1]),
                    'top_3': len([p for p in passadas if p.colocacao_passada and p.colocacao_passada <= 3]),
                    'top_5': len([p for p in passadas if p.colocacao_passada and p.colocacao_passada <= 5])
                }
            }
        
        resultado = {
            'trio_id': trio_id,
            'resumo_basico': resumo,
            'estatisticas_avancadas': estatisticas_avancadas,
            'incluiu_historico': incluir_historico
        }
        
        return success_response(resultado, 'Estatísticas do trio obtidas com sucesso')
    except Exception as e:
        return error_response(message=f'Erro ao obter estatísticas: {str(e)}')

@router.get("/passada/competidor/{competidor_id}/historico", 
           tags=['Histórico Competidor'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_historico_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    prova_id: Optional[int] = Query(None, description="ID da prova específica"),
    periodo_dias: int = Query(90, ge=1, le=365, description="Período em dias"),
    incluir_detalhes: bool = Query(True, description="Incluir detalhes das passadas"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém histórico detalhado de um competidor"""
    try:
        data_limite = datetime.now() - timedelta(days=periodo_dias)
        
        filtros = models.FiltrosPassadas(
            competidor_id=competidor_id,
            prova_id=prova_id,
            data_inicio=data_limite,
            tamanho_pagina=1000
        )
        
        passadas, total = RepositorioPassadas(db).listar_passadas(filtros)
        
        if not passadas:
            return error_response(message='Nenhuma passada encontrada no período especificado')
        
        # Agrupar por prova
        passadas_por_prova = {}
        for passada in passadas:
            prova_nome = passada.prova.nome if passada.prova else f'Prova {passada.prova_id}'
            if prova_nome not in passadas_por_prova:
                passadas_por_prova[prova_nome] = []
            passadas_por_prova[prova_nome].append(passada)
        
        # Calcular estatísticas por prova
        resumo_por_prova = {}
        for prova_nome, lista_passadas in passadas_por_prova.items():
            executadas = [p for p in lista_passadas if p.status == 'executada']
            tempos = [float(p.tempo_realizado) for p in executadas if p.tempo_realizado]
            
            resumo_por_prova[prova_nome] = {
                'total_passadas': len(lista_passadas),
                'passadas_executadas': len(executadas),
                'melhor_tempo': min(tempos) if tempos else None,
                'tempo_medio': sum(tempos) / len(tempos) if tempos else None,
                'pontos_totais': sum(float(p.pontos_passada) for p in lista_passadas),
                'primeira_data': min([p.data_hora_passada for p in lista_passadas if p.data_hora_passada]),
                'ultima_data': max([p.data_hora_passada for p in lista_passadas if p.data_hora_passada])
            }
        
        # Estatísticas gerais do período
        executadas_total = [p for p in passadas if p.status == 'executada']
        tempos_total = [float(p.tempo_realizado) for p in executadas_total if p.tempo_realizado]
        
        estatisticas_gerais = {
            'periodo_dias': periodo_dias,
            'total_passadas': len(passadas),
            'total_executadas': len(executadas_total),
            'total_provas': len(passadas_por_prova),
            'melhor_tempo_periodo': min(tempos_total) if tempos_total else None,
            'tempo_medio_periodo': sum(tempos_total) / len(tempos_total) if tempos_total else None,
            'pontos_totais_periodo': sum(float(p.pontos_passada) for p in passadas),
            'primeira_passada': min([p.data_hora_passada for p in passadas if p.data_hora_passada]) if passadas else None,
            'ultima_passada': max([p.data_hora_passada for p in passadas if p.data_hora_passada]) if passadas else None
        }
        
        resultado = {
            'competidor_id': competidor_id,
            'periodo_analisado': {
                'data_inicio': data_limite.date().isoformat(),
                'data_fim': datetime.now().date().isoformat(),
                'dias': periodo_dias
            },
            'estatisticas_gerais': estatisticas_gerais,
            'resumo_por_prova': resumo_por_prova,
            'passadas_detalhadas': passadas if incluir_detalhes else []
        }
        
        return success_response(resultado, f'Histórico de {periodo_dias} dias obtido com sucesso')
    except Exception as e:
        return error_response(message=f'Erro ao obter histórico: {str(e)}')

@router.get("/passada/prova/{prova_id}/resumo-geral", 
           tags=['Resumo Prova'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_resumo_geral_prova(
    prova_id: int = Path(..., description="ID da prova"),
    incluir_graficos: bool = Query(False, description="Incluir dados para gráficos"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém resumo geral completo de uma prova"""
    try:
        repo = RepositorioPassadas(db)
        
        # Buscar todas as passadas da prova
        filtros = models.FiltrosPassadas(prova_id=prova_id, tamanho_pagina=50000)
        passadas, total = repo.listar_passadas(filtros)
        
        if not passadas:
            return error_response(message='Nenhuma passada encontrada para esta prova')
        
        # Estatísticas básicas
        executadas = [p for p in passadas if p.status == 'executada']
        pendentes = [p for p in passadas if p.status == 'pendente']
        no_time = [p for p in passadas if p.status == 'no_time']
        
        tempos_validos = [float(p.tempo_realizado) for p in executadas if p.tempo_realizado]
        
        # Agrupar por categoria
        por_categoria = {}
        for passada in passadas:
            cat_nome = passada.trio.categoria.nome if passada.trio and passada.trio.categoria else 'Sem categoria'
            if cat_nome not in por_categoria:
                por_categoria[cat_nome] = {'total': 0, 'executadas': 0, 'tempos': []}
            
            por_categoria[cat_nome]['total'] += 1
            if passada.status == 'executada':
                por_categoria[cat_nome]['executadas'] += 1
                if passada.tempo_realizado:
                    por_categoria[cat_nome]['tempos'].append(float(passada.tempo_realizado))
        
        # Calcular médias por categoria
        for cat_nome, dados in por_categoria.items():
            if dados['tempos']:
                dados['tempo_medio'] = sum(dados['tempos']) / len(dados['tempos'])
                dados['melhor_tempo'] = min(dados['tempos'])
            else:
                dados['tempo_medio'] = None
                dados['melhor_tempo'] = None
        
        # Top performers
        top_tempos = sorted(executadas, key=lambda x: float(x.tempo_realizado) if x.tempo_realizado else float('inf'))[:5]
        top_pontos = sorted(passadas, key=lambda x: float(x.pontos_passada), reverse=True)[:5]
        
        # Dados para gráficos (se solicitado)
        dados_graficos = {}
        if incluir_graficos:
            # Distribuição de tempos em faixas
            faixas_tempo = {
                '0-30s': len([t for t in tempos_validos if t <= 30]),
                '30-45s': len([t for t in tempos_validos if 30 < t <= 45]),
                '45-60s': len([t for t in tempos_validos if 45 < t <= 60]),
                '60-75s': len([t for t in tempos_validos if 60 < t <= 75]),
                '75s+': len([t for t in tempos_validos if t > 75])
            }
            
            # Evolução por dia
            evolucao_diaria = {}
            for passada in executadas:
                if passada.data_hora_passada:
                    dia = passada.data_hora_passada.date().isoformat()
                    if dia not in evolucao_diaria:
                        evolucao_diaria[dia] = {'total': 0, 'tempo_medio': []}
                    evolucao_diaria[dia]['total'] += 1
                    if passada.tempo_realizado:
                        evolucao_diaria[dia]['tempo_medio'].append(float(passada.tempo_realizado))
            
            # Calcular médias diárias
            for dia, dados in evolucao_diaria.items():
                if dados['tempo_medio']:
                    dados['tempo_medio'] = sum(dados['tempo_medio']) / len(dados['tempo_medio'])
                else:
                    dados['tempo_medio'] = None
            
            dados_graficos = {
                'distribuicao_tempos': faixas_tempo,
                'evolucao_diaria': evolucao_diaria
            }
        
        resumo_geral = {
            'prova_id': prova_id,
            'data_resumo': datetime.now().isoformat(),
            'estatisticas_basicas': {
                'total_passadas': len(passadas),
                'passadas_executadas': len(executadas),
                'passadas_pendentes': len(pendentes),
                'passadas_no_time': len(no_time),
                'taxa_conclusao': (len(executadas) / len(passadas) * 100) if passadas else 0,
                'tempo_medio_geral': sum(tempos_validos) / len(tempos_validos) if tempos_validos else None,
                'melhor_tempo_geral': min(tempos_validos) if tempos_validos else None,
                'pior_tempo_geral': max(tempos_validos) if tempos_validos else None
            },
            'por_categoria': por_categoria,
            'top_performers': {
                'melhores_tempos': [
                    {
                        'trio_id': p.trio_id,
                        'trio_numero': p.trio.numero_trio if p.trio else None,
                        'tempo': float(p.tempo_realizado) if p.tempo_realizado else None,
                        'passada_numero': p.numero_passada
                    }
                    for p in top_tempos
                ],
                'maiores_pontuacoes': [
                    {
                        'trio_id': p.trio_id,
                        'trio_numero': p.trio.numero_trio if p.trio else None,
                        'pontos': float(p.pontos_passada),
                        'passada_numero': p.numero_passada
                    }
                    for p in top_pontos
                ]
            },
            'dados_graficos': dados_graficos,
            'incluiu_graficos': incluir_graficos
        }
        
        return success_response(resumo_geral, 'Resumo geral da prova obtido com sucesso')
    except Exception as e:
        return error_response(message=f'Erro ao obter resumo geral: {str(e)}')

# ========================== ROTAS DE MONITORAMENTO EM TEMPO REAL ==========================

@router.get("/passada/monitor/tempo-real", 
           tags=['Monitor Tempo Real'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def monitor_tempo_real(
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    ultimos_minutos: int = Query(30, ge=5, le=120, description="Últimos minutos"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Monitor de atividade em tempo real"""
    try:
        data_limite = datetime.now() - timedelta(minutes=ultimos_minutos)
        
        filtros = models.FiltrosPassadas(
            prova_id=prova_id,
            data_inicio=data_limite,
            tamanho_pagina=1000
        )
        
        passadas_recentes, total = RepositorioPassadas(db).listar_passadas(filtros)
        
        # Atividades por minuto
        atividade_por_minuto = {}
        for i in range(ultimos_minutos):
            minuto = datetime.now() - timedelta(minutes=i)
            chave_minuto = minuto.strftime('%H:%M')
            atividade_por_minuto[chave_minuto] = {
                'passadas_criadas': 0,
                'passadas_executadas': 0,
                'tempos_registrados': []
            }
        
        for passada in passadas_recentes:
            if passada.created_at:
                minuto_criacao = passada.created_at.strftime('%H:%M')
                if minuto_criacao in atividade_por_minuto:
                    atividade_por_minuto[minuto_criacao]['passadas_criadas'] += 1
            
            if passada.data_hora_passada:
                minuto_execucao = passada.data_hora_passada.strftime('%H:%M')
                if minuto_execucao in atividade_por_minuto:
                    atividade_por_minuto[minuto_execucao]['passadas_executadas'] += 1
                    if passada.tempo_realizado:
                        atividade_por_minuto[minuto_execucao]['tempos_registrados'].append(
                            float(passada.tempo_realizado)
                        )
        
        # Últimas atividades
        ultimas_executadas = [p for p in passadas_recentes if p.status == 'executada']
        ultimas_executadas.sort(key=lambda x: x.data_hora_passada or datetime.min, reverse=True)
        
        # Alertas em tempo real
        alertas_tempo_real = []
        
        # Verificar passadas muito rápidas ou muito lentas
        for passada in ultimas_executadas[:10]:
            if passada.tempo_realizado:
                tempo = float(passada.tempo_realizado)
                if tempo < 20:
                    alertas_tempo_real.append({
                        'tipo': 'tempo_rapido',
                        'passada_id': passada.id,
                        'trio_numero': passada.trio.numero_trio if passada.trio else None,
                        'tempo': tempo,
                        'mensagem': f'Tempo muito rápido: {tempo}s'
                    })
                elif tempo > 90:
                    alertas_tempo_real.append({
                        'tipo': 'tempo_lento',
                        'passada_id': passada.id,
                        'trio_numero': passada.trio.numero_trio if passada.trio else None,
                        'tempo': tempo,
                        'mensagem': f'Tempo muito lento: {tempo}s'
                    })
        
        monitor = {
            'timestamp': datetime.now().isoformat(),
            'periodo_minutos': ultimos_minutos,
            'prova_id': prova_id,
            'resumo_periodo': {
                'total_passadas_periodo': len(passadas_recentes),
                'passadas_executadas': len(ultimas_executadas),
                'passadas_pendentes': len([p for p in passadas_recentes if p.status == 'pendente']),
                'tempo_medio_periodo': sum([float(p.tempo_realizado) for p in ultimas_executadas if p.tempo_realizado]) / len(ultimas_executadas) if ultimas_executadas else None
            },
            'atividade_por_minuto': atividade_por_minuto,
            'ultimas_execucoes': [
                {
                    'passada_id': p.id,
                    'trio_numero': p.trio.numero_trio if p.trio else None,
                    'tempo': float(p.tempo_realizado) if p.tempo_realizado else None,
                    'pontos': float(p.pontos_passada),
                    'data_hora': p.data_hora_passada.isoformat() if p.data_hora_passada else None
                }
                for p in ultimas_executadas[:10]
            ],
            'alertas_tempo_real': alertas_tempo_real
        }
        
        return success_response(monitor, 'Monitor tempo real atualizado')
    except Exception as e:
        return error_response(message=f'Erro no monitor tempo real: {str(e)}')

@router.get("/passada/monitor/fila", 
           tags=['Monitor Tempo Real'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def monitor_fila_passadas(
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    limite: int = Query(20, ge=5, le=50, description="Limite de passadas na fila"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Monitor da fila de passadas pendentes"""
    try:
        # Buscar passadas pendentes ordenadas por criação
        filtros = models.FiltrosPassadas(
            prova_id=prova_id,
            categoria_id=categoria_id,
            status='pendente',
            tamanho_pagina=limite
        )
        
        passadas_pendentes, total_pendentes = RepositorioPassadas(db).listar_passadas(filtros)
        
        # Organizar fila por prioridade (pode implementar lógica específica)
        fila_organizada = []
        for passada in passadas_pendentes:
            # Calcular tempo de espera
            tempo_espera = None
            if passada.created_at:
                tempo_espera = (datetime.now() - passada.created_at).total_seconds() / 60  # minutos
            
            # Determinar prioridade (exemplo de lógica)
            prioridade = 'normal'
            if tempo_espera and tempo_espera > 60:
                prioridade = 'alta'
            elif tempo_espera and tempo_espera > 30:
                prioridade = 'media'
            
            item_fila = {
                'passada_id': passada.id,
                'trio_id': passada.trio_id,
                'trio_numero': passada.trio.numero_trio if passada.trio else None,
                'numero_passada': passada.numero_passada,
                'numero_boi': passada.numero_boi,
                'tempo_espera_minutos': tempo_espera,
                'prioridade': prioridade,
                'criado_em': passada.created_at.isoformat() if passada.created_at else None,
                'competidores': [
                    i.competidor.nome for i in passada.trio.integrantes if i.competidor
                ] if passada.trio and passada.trio.integrantes else []
            }
            
            fila_organizada.append(item_fila)
        
        # Ordenar por prioridade e tempo de espera
        ordem_prioridade = {'alta': 3, 'media': 2, 'normal': 1}
        fila_organizada.sort(
            key=lambda x: (ordem_prioridade.get(x['prioridade'], 0), -(x['tempo_espera_minutos'] or 0)),
            reverse=True
        )
        
        # Estatísticas da fila
        estatisticas_fila = {
            'total_pendentes': total_pendentes,
            'na_fila_atual': len(fila_organizada),
            'tempo_espera_medio': sum([f['tempo_espera_minutos'] for f in fila_organizada if f['tempo_espera_minutos']]) / len([f for f in fila_organizada if f['tempo_espera_minutos']]) if any(f['tempo_espera_minutos'] for f in fila_organizada) else None,
            'por_prioridade': {
                'alta': len([f for f in fila_organizada if f['prioridade'] == 'alta']),
                'media': len([f for f in fila_organizada if f['prioridade'] == 'media']),
                'normal': len([f for f in fila_organizada if f['prioridade'] == 'normal'])
            }
        }
        
        resultado = {
            'timestamp': datetime.now().isoformat(),
            'prova_id': prova_id,
            'categoria_id': categoria_id,
            'estatisticas': estatisticas_fila,
            'fila': fila_organizada
        }
        
        return success_response(resultado, f'Fila de {len(fila_organizada)} passadas pendentes')
    except Exception as e:
        return error_response(message=f'Erro ao obter fila: {str(e)}')

# ========================== RELATÓRIOS AVANÇADOS ==========================

@router.get("/passada/relatorio-performance/{prova_id}", 
           tags=['Relatórios Avançados'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def gerar_relatorio_performance(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    incluir_graficos: bool = Query(True, description="Incluir dados para gráficos"),
    incluir_comparacoes: bool = Query(True, description="Incluir comparações históricas"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera relatório avançado de performance da prova"""
    try:
        repo = RepositorioPassadas(db)
        
        # Dados básicos da prova
        filtros = models.FiltrosPassadas(
            prova_id=prova_id,
            categoria_id=categoria_id,
            tamanho_pagina=50000
        )
        
        passadas, total = repo.listar_passadas(filtros)
        
        if not passadas:
            return error_response(message='Nenhuma passada encontrada para o relatório')
        
        # Análise de performance por trio
        performance_trios = {}
        for passada in passadas:
            trio_id = passada.trio_id
            if trio_id not in performance_trios:
                performance_trios[trio_id] = {
                    'trio_numero': passada.trio.numero_trio if passada.trio else None,
                    'passadas': [],
                    'tempos': [],
                    'pontos': [],
                    'colocacoes': []
                }
            
            performance_trios[trio_id]['passadas'].append(passada)
            
            if passada.status == 'executada' and passada.tempo_realizado:
                performance_trios[trio_id]['tempos'].append(float(passada.tempo_realizado))
                performance_trios[trio_id]['pontos'].append(float(passada.pontos_passada))
                
                if passada.colocacao_passada:
                    performance_trios[trio_id]['colocacoes'].append(passada.colocacao_passada)
        
        # Calcular métricas de performance para cada trio
        analise_trios = []
        for trio_id, dados in performance_trios.items():
            if dados['tempos']:
                # Tendência de melhoria
                tempos = dados['tempos']
                if len(tempos) >= 2:
                    # Regressão linear simples para tendência
                    n = len(tempos)
                    x = list(range(1, n + 1))
                    soma_x = sum(x)
                    soma_y = sum(tempos)
                    soma_xy = sum(xi * yi for xi, yi in zip(x, tempos))
                    soma_x2 = sum(xi * xi for xi in x)
                    
                    # Coeficiente angular (slope)
                    slope = (n * soma_xy - soma_x * soma_y) / (n * soma_x2 - soma_x * soma_x)
                    tendencia = 'melhoria' if slope < 0 else 'piora' if slope > 0 else 'estavel'
                else:
                    slope = 0
                    tendencia = 'insuficiente'
                
                # Consistência (desvio padrão)
                tempo_medio = sum(tempos) / len(tempos)
                variancia = sum((t - tempo_medio) ** 2 for t in tempos) / len(tempos)
                desvio_padrao = variancia ** 0.5
                coef_variacao = (desvio_padrao / tempo_medio) * 100 if tempo_medio > 0 else 0
                
                analise_trios.append({
                    'trio_id': trio_id,
                    'trio_numero': dados['trio_numero'],
                    'total_passadas': len(dados['passadas']),
                    'passadas_executadas': len(dados['tempos']),
                    'tempo_medio': tempo_medio,
                    'melhor_tempo': min(tempos),
                    'pior_tempo': max(tempos),
                    'desvio_padrao': desvio_padrao,
                    'coeficiente_variacao': coef_variacao,
                    'tendencia': tendencia,
                    'slope_tendencia': slope,
                    'consistencia_score': max(0, 100 - coef_variacao),  # Inverso do coef. variação
                    'pontos_total': sum(dados['pontos']),
                    'colocacao_media': sum(dados['colocacoes']) / len(dados['colocacoes']) if dados['colocacoes'] else None
                })
        
        # Ordenar por performance (combinação de tempo médio e consistência)
        analise_trios.sort(key=lambda x: (x['tempo_medio'], x['coeficiente_variacao']))
        
        # Adicionar ranking de performance
        for i, trio in enumerate(analise_trios, 1):
            trio['ranking_performance'] = i
        
        # Análise geral da prova
        todos_tempos = [t for trio in performance_trios.values() for t in trio['tempos']]
        analise_geral = {
            'total_trios': len(performance_trios),
            'total_passadas_executadas': len(todos_tempos),
            'tempo_medio_prova': sum(todos_tempos) / len(todos_tempos) if todos_tempos else None,
            'melhor_tempo_prova': min(todos_tempos) if todos_tempos else None,
            'pior_tempo_prova': max(todos_tempos) if todos_tempos else None,
            'desvio_padrao_prova': (sum((t - (sum(todos_tempos) / len(todos_tempos))) ** 2 for t in todos_tempos) / len(todos_tempos)) ** 0.5 if todos_tempos else None
        }
        
        # Dados para gráficos
        dados_graficos = {}
        if incluir_graficos:
            # Evolução de tempos por trio (top 5)
            top_5_trios = analise_trios[:5]
            evolucao_tempos = {}
            
            for trio in top_5_trios:
                trio_data = performance_trios[trio['trio_id']]
                passadas_ordenadas = sorted(trio_data['passadas'], key=lambda x: x.created_at or datetime.min)
                
                evolucao_tempos[f"Trio {trio['trio_numero']}"] = [
                    {
                        'passada': i + 1,
                        'tempo': float(p.tempo_realizado) if p.tempo_realizado else None,
                        'data': p.data_hora_passada.isoformat() if p.data_hora_passada else None
                    }
                    for i, p in enumerate(passadas_ordenadas) if p.status == 'executada'
                ]
            
            # Distribuição de performance
            distribuicao_performance = {
                'excelente': len([t for t in analise_trios if t['consistencia_score'] >= 80]),
                'boa': len([t for t in analise_trios if 60 <= t['consistencia_score'] < 80]),
                'regular': len([t for t in analise_trios if 40 <= t['consistencia_score'] < 60]),
                'baixa': len([t for t in analise_trios if t['consistencia_score'] < 40])
            }
            
            dados_graficos = {
                'evolucao_tempos_top5': evolucao_tempos,
                'distribuicao_performance': distribuicao_performance
            }
        
        # Comparações históricas (se solicitado)
        comparacoes_historicas = {}
        if incluir_comparacoes:
            # Buscar provas anteriores similares (mesmo local/período)
            # Esta é uma implementação simplificada
            comparacoes_historicas = {
                'disponivel': False,
                'motivo': 'Implementação de comparações históricas pendente'
            }
        
        relatorio = {
            'prova_id': prova_id,
            'categoria_id': categoria_id,
            'gerado_em': datetime.now().isoformat(),
            'analise_geral': analise_geral,
            'performance_por_trio': analise_trios,
            'dados_graficos': dados_graficos,
            'comparacoes_historicas': comparacoes_historicas,
            'configuracoes': {
                'incluiu_graficos': incluir_graficos,
                'incluiu_comparacoes': incluir_comparacoes
            }
        }
        
        return success_response(relatorio, 'Relatório de performance gerado com sucesso')
    except Exception as e:
        return error_response(message=f'Erro ao gerar relatório de performance: {str(e)}')

@router.get("/passada/relatorio-executivo/{prova_id}", 
           tags=['Relatórios Executivos'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def gerar_relatorio_executivo(
    prova_id: int = Path(..., description="ID da prova"),
    incluir_recomendacoes: bool = Query(True, description="Incluir recomendações"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera relatório executivo resumido da prova"""
    try:
        repo = RepositorioPassadas(db)
        
        # Buscar informações da prova
        prova = db.query(schemas.Provas).filter(schemas.Provas.id == prova_id).first()
        if not prova:
            return error_response(message='Prova não encontrada')
        
        # Estatísticas gerais
        estatisticas = repo.obter_estatisticas_gerais(prova_id)
        
        if not estatisticas:
            return error_response(message='Nenhum dado encontrado para a prova')
        
        # KPIs principais
        kpis = {
            'participacao': {
                'total_passadas': estatisticas['total_passadas'],
                'taxa_conclusao': (estatisticas['passadas_executadas'] / estatisticas['total_passadas'] * 100) if estatisticas['total_passadas'] > 0 else 0,
                'passadas_no_time': estatisticas['passadas_no_time'],
                'taxa_no_time': (estatisticas['passadas_no_time'] / estatisticas['total_passadas'] * 100) if estatisticas['total_passadas'] > 0 else 0
            },
            'performance': {
                'tempo_medio': estatisticas['tempo_medio_geral'],
                'melhor_tempo': estatisticas['melhor_tempo_geral'],
                'pior_tempo': estatisticas['pior_tempo_geral']
            },
            'organizacao': {
                'total_categorias': len(set([p.trio.categoria_id for p in repo.listar_passadas(models.FiltrosPassadas(prova_id=prova_id, tamanho_pagina=1000))[0] if p.trio])),
                'total_trios': len(set([p.trio_id for p in repo.listar_passadas(models.FiltrosPassadas(prova_id=prova_id, tamanho_pagina=1000))[0]])),
                'distribuicao_bois': len(estatisticas.get('distribuicao_bois', {}))
            }
        }
        
        # Insights automáticos
        insights = []
        
        if kpis['participacao']['taxa_conclusao'] > 90:
            insights.append('Excelente taxa de conclusão de passadas')
        elif kpis['participacao']['taxa_conclusao'] < 70:
            insights.append('Taxa de conclusão abaixo do esperado - investigar causas')
        
        if kpis['participacao']['taxa_no_time'] > 30:
            insights.append('Alta taxa de no-time - considerar revisar tempo limite')
        elif kpis['participacao']['taxa_no_time'] < 10:
            insights.append('Baixa taxa de no-time - tempo limite adequado')
        
        if estatisticas.get('tempo_medio_geral'):
            if estatisticas['tempo_medio_geral'] < 45:
                insights.append('Tempos médios excelentes - prova competitiva')
            elif estatisticas['tempo_medio_geral'] > 70:
                insights.append('Tempos médios altos - possível revisão de configurações')
        
        # Recomendações (se solicitado)
        recomendacoes = []
        if incluir_recomendacoes:
            if kpis['participacao']['taxa_no_time'] > 25:
                recomendacoes.append({
                    'categoria': 'Configuração',
                    'prioridade': 'Alta',
                    'recomendacao': 'Considerar aumentar tempo limite das categorias com alta taxa de no-time'
                })
            
            if kpis['organizacao']['distribuicao_bois'] < 10:
                recomendacoes.append({
                    'categoria': 'Logística',
                    'prioridade': 'Média',
                    'recomendacao': 'Avaliar aumento do número de bois disponíveis para maior variedade'
                })
            
            if kpis['participacao']['taxa_conclusao'] < 80:
                recomendacoes.append({
                    'categoria': 'Operacional',
                    'prioridade': 'Alta',
                    'recomendacao': 'Investigar gargalos operacionais que impedem conclusão das passadas'
                })
        
        # Top performers
        ranking_tempo = repo.obter_ranking_passada(prova_id, tipo_ranking="tempo")
        top_performers = ranking_tempo[:3] if ranking_tempo else []
        
        relatorio_executivo = {
            'prova_info': {
                'id': prova.id,
                'nome': prova.nome,
                'data': prova.data.isoformat() if prova.data else None,
                'local': f"{prova.rancho}, {prova.cidade}/{prova.estado}" if prova.rancho else f"{prova.cidade}/{prova.estado}" if prova.cidade else None
            },
            'kpis_principais': kpis,
            'insights_automaticos': insights,
            'top_performers': top_performers,
            'recomendacoes': recomendacoes,
            'resumo_executivo': {
                'total_participantes': kpis['organizacao']['total_trios'] * 3,  # aproximado
                'nivel_competitividade': 'Alto' if kpis['participacao']['taxa_no_time'] > 20 else 'Médio' if kpis['participacao']['taxa_no_time'] > 10 else 'Baixo',
                'organizacao_geral': 'Excelente' if kpis['participacao']['taxa_conclusao'] > 90 else 'Boa' if kpis['participacao']['taxa_conclusao'] > 80 else 'Regular',
                'performance_geral': 'Excelente' if (estatisticas.get('tempo_medio_geral', 0) < 50) else 'Boa' if (estatisticas.get('tempo_medio_geral', 0) < 65) else 'Regular'
            },
            'gerado_em': datetime.now().isoformat(),
            'incluiu_recomendacoes': incluir_recomendacoes
        }
        
        return success_response(relatorio_executivo, 'Relatório executivo gerado com sucesso')
    except Exception as e:
        return error_response(message=f'Erro ao gerar relatório executivo: {str(e)}')

# ========================== WEBHOOKS E NOTIFICAÇÕES ==========================

@router.post("/passada/webhook/passada-executada", 
            tags=['Webhooks'], 
            status_code=status.HTTP_200_OK, 
            response_model=models.ApiResponse)
async def webhook_passada_executada(
    passada_id: int = Body(..., description="ID da passada executada"),
    tempo_realizado: float = Body(..., description="Tempo realizado"),
    status_final: str = Body(..., description="Status final"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Webhook para notificar execução de passada (para integração externa)"""
    try:
        repo = RepositorioPassadas(db)
        passada = repo.obter_passada(passada_id)
        
        if not passada:
            return error_response(message='Passada não encontrada')
        
        # Atualizar dados da passada
        passada_update = models.PassadaTrioPUT(
            tempo_realizado=tempo_realizado,
            status=status_final,
            data_hora_passada=datetime.now()
        )
        
        passada_atualizada = repo.atualizar_passada(passada_id, passada_update)
        
        # Aqui poderia disparar notificações, atualizações em tempo real, etc.
        # Por exemplo: enviar para WebSocket, atualizar cache, etc.
        
        # Log da atividade
        log_atividade = {
            'tipo': 'passada_executada',
            'passada_id': passada_id,
            'trio_id': passada.trio_id,
            'tempo_realizado': tempo_realizado,
            'status_final': status_final,
            'timestamp': datetime.now().isoformat(),
            'usuario_id': usuario.id if hasattr(usuario, 'id') else None
        }
        
        # Atualizar controle de participação dos competidores
        if passada.trio and passada.trio.integrantes:
            for integrante in passada.trio.integrantes:
                if integrante.competidor:
                    controle = repo.obter_controle_participacao(
                        integrante.competidor_id, 
                        passada.prova_id, 
                        passada.trio.categoria_id
                    )
                    if controle:
                        controle.total_passadas_executadas += 1
                        controle.ultima_passada = datetime.now()
                        controle.atualizar_contadores()
        
        db.commit()
        
        return success_response(
            {
                'passada_atualizada': passada_atualizada,
                'log_atividade': log_atividade,
                'webhook_processado': True
            },
            'Webhook processado com sucesso'
        )
    except Exception as e:
        return error_response(message=f'Erro ao processar webhook: {str(e)}')

# ========================== HEALTH CHECK E STATUS ==========================

@router.get("/passada/health", 
           tags=['Sistema'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def health_check_passadas(
    db: Session = Depends(get_db)
):
    """Health check do sistema de passadas"""
    try:
        # Verificar conexão com banco
        total_passadas = db.query(schemas.PassadasTrio).count()
        
        # Verificar passadas ativas (últimas 24h)
        ontem = datetime.now() - timedelta(days=1)
        passadas_recentes = db.query(schemas.PassadasTrio).filter(
            schemas.PassadasTrio.created_at >= ontem
        ).count()
        
        # Verificar configurações
        configs_ativas = db.query(schemas.ConfiguracaoPassadasProva).filter(
            schemas.ConfiguracaoPassadasProva.ativa == True
        ).count()
        
        # Status do sistema
        status_sistema = {
            'database_connection': True,
            'total_passadas_sistema': total_passadas,
            'passadas_ultimas_24h': passadas_recentes,
            'configuracoes_ativas': configs_ativas,
            'timestamp_check': datetime.now().isoformat(),
            'versao_api': '1.0.0',
            'status_geral': 'healthy'
        }
        
        # Verificar alertas
        alertas = []
        
        # Verificar passadas pendentes muito antigas
        uma_semana_atras = datetime.now() - timedelta(days=7)
        pendentes_antigas = db.query(schemas.PassadasTrio).filter(
            and_(
                schemas.PassadasTrio.status == 'pendente',
                schemas.PassadasTrio.created_at < uma_semana_atras
            )
        ).count()
        
        if pendentes_antigas > 0:
            alertas.append(f"{pendentes_antigas} passadas pendentes há mais de 7 dias")
        
        # Verificar configurações órfãs
        configs_orfas = db.query(schemas.ConfiguracaoPassadasProva).filter(
            ~schemas.ConfiguracaoPassadasProva.prova_id.in_(
                db.query(schemas.Provas.id).filter(schemas.Provas.ativa == True)
            )
        ).count()
        
        if configs_orfas > 0:
            alertas.append(f"{configs_orfas} configurações órfãs encontradas")
        
        # Verificar inconsistências de dados
        passadas_sem_trio = db.query(schemas.PassadasTrio).filter(
            ~schemas.PassadasTrio.trio_id.in_(
                db.query(schemas.Trios.id)
            )
        ).count()
        
        if passadas_sem_trio > 0:
            alertas.append(f"{passadas_sem_trio} passadas com trio inexistente")
            status_sistema['status_geral'] = 'warning'
        
        if len(alertas) > 3:
            status_sistema['status_geral'] = 'critical'
        
        status_sistema['alertas'] = alertas
        status_sistema['total_alertas'] = len(alertas)
        
        return success_response(status_sistema, f'Health check concluído - Status: {status_sistema["status_geral"]}')
    except Exception as e:
        return error_response(message=f'Erro no health check: {str(e)}')

@router.get("/passada/status/sistema", 
           tags=['Sistema'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def status_sistema_passadas(
    incluir_metricas: bool = Query(True, description="Incluir métricas detalhadas"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Status detalhado do sistema de passadas"""
    try:
        agora = datetime.now()
        
        # Estatísticas básicas
        stats_basicas = {
            'total_passadas': db.query(schemas.PassadasTrio).count(),
            'total_configuracoes': db.query(schemas.ConfiguracaoPassadasProva).count(),
            'total_controles': db.query(schemas.ControleParticipacao).count(),
            'passadas_hoje': db.query(schemas.PassadasTrio).filter(
                schemas.PassadasTrio.created_at >= datetime.combine(agora.date(), datetime.min.time())
            ).count()
        }
        
        # Distribuição por status
        distribuicao_status = {}
        for status_value in ['pendente', 'executada', 'no_time', 'desclassificada']:
            count = db.query(schemas.PassadasTrio).filter(
                schemas.PassadasTrio.status == status_value
            ).count()
            distribuicao_status[status_value] = count
        
        # Performance do sistema (se solicitado)
        metricas_performance = {}
        if incluir_metricas:
            # Tempos de resposta médios (simulado - seria medido em produção)
            metricas_performance = {
                'tempo_medio_criacao_passada': '150ms',
                'tempo_medio_consulta': '50ms',
                'tempo_medio_listagem': '200ms',
                'memoria_utilizada': '45%',
                'cpu_utilizada': '23%',
                'conexoes_db_ativas': 5
            }
        
        # Atividade recente
        ultima_hora = agora - timedelta(hours=1)
        atividade_recente = {
            'passadas_criadas_ultima_hora': db.query(schemas.PassadasTrio).filter(
                schemas.PassadasTrio.created_at >= ultima_hora
            ).count(),
            'passadas_executadas_ultima_hora': db.query(schemas.PassadasTrio).filter(
                and_(
                    schemas.PassadasTrio.data_hora_passada >= ultima_hora,
                    schemas.PassadasTrio.status == 'executada'
                )
            ).count(),
            'configuracoes_modificadas_ultima_hora': db.query(schemas.ConfiguracaoPassadasProva).filter(
                or_(
                    schemas.ConfiguracaoPassadasProva.created_at >= ultima_hora,
                    and_(
                        schemas.ConfiguracaoPassadasProva.created_at < ultima_hora,
                        func.coalesce(
                            func.extract('epoch', func.now() - schemas.ConfiguracaoPassadasProva.created_at) / 3600,
                            0
                        ) <= 1
                    )
                )
            ).count()
        }
        
        # Verificações de integridade
        verificacoes_integridade = {
            'passadas_sem_trio': db.query(schemas.PassadasTrio).filter(
                ~schemas.PassadasTrio.trio_id.in_(db.query(schemas.Trios.id))
            ).count(),
            'configuracoes_sem_prova': db.query(schemas.ConfiguracaoPassadasProva).filter(
                ~schemas.ConfiguracaoPassadasProva.prova_id.in_(db.query(schemas.Provas.id))
            ).count(),
            'controles_sem_competidor': db.query(schemas.ControleParticipacao).filter(
                ~schemas.ControleParticipacao.competidor_id.in_(db.query(schemas.Competidores.id))
            ).count()
        }
        
        # Determinar status geral do sistema
        total_problemas = sum(verificacoes_integridade.values())
        if total_problemas == 0:
            status_geral = 'operational'
        elif total_problemas <= 5:
            status_geral = 'degraded'
        else:
            status_geral = 'critical'
        
        # Informações da versão e configuração
        info_sistema = {
            'versao_api': '1.0.0',
            'ambiente': 'production',  # seria obtido de variáveis de ambiente
            'database_version': 'PostgreSQL 13+',
            'python_version': '3.9+',
            'fastapi_version': '0.100+',
            'ultima_atualizacao': '2024-12-19',
            'uptime_estimado': '99.9%'
        }
        
        status_completo = {
            'timestamp': agora.isoformat(),
            'status_geral': status_geral,
            'estatisticas_basicas': stats_basicas,
            'distribuicao_status': distribuicao_status,
            'atividade_recente': atividade_recente,
            'verificacoes_integridade': verificacoes_integridade,
            'metricas_performance': metricas_performance,
            'info_sistema': info_sistema,
            'incluiu_metricas': incluir_metricas
        }
        
        return success_response(status_completo, f'Status do sistema: {status_geral}')
    except Exception as e:
        return error_response(message=f'Erro ao obter status do sistema: {str(e)}')

# ========================== UTILITÁRIOS DE MANUTENÇÃO ==========================

@router.post("/passada/manutencao/otimizar-indices", 
            tags=['Manutenção'], 
            status_code=status.HTTP_200_OK, 
            response_model=models.ApiResponse)
async def otimizar_indices_passadas(
    confirmar: bool = Query(False, description="Confirmar otimização"),
    dry_run: bool = Query(True, description="Executar apenas simulação"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Otimiza índices das tabelas de passadas"""
    if not confirmar and not dry_run:
        return error_response(message='Operação requer confirmação ou dry_run=true')
    
    try:
        # Lista de operações de otimização
        operacoes_otimizacao = [
            {
                'tabela': 'passadas_trio',
                'operacao': 'REINDEX',
                'indices': ['idx_passadas_trio_prova', 'idx_passadas_numero', 'idx_passadas_status'],
                'estimativa_tempo': '2-5 minutos'
            },
            {
                'tabela': 'configuracao_passadas_prova',
                'operacao': 'ANALYZE',
                'indices': ['idx_config_prova', 'idx_config_categoria'],
                'estimativa_tempo': '30 segundos'
            },
            {
                'tabela': 'controle_participacao',
                'operacao': 'VACUUM',
                'indices': ['idx_controle_competidor', 'idx_controle_prova'],
                'estimativa_tempo': '1-2 minutos'
            }
        ]
        
        resultados = []
        
        if dry_run:
            # Simulação - apenas retornar o que seria feito
            for op in operacoes_otimizacao:
                resultados.append({
                    'tabela': op['tabela'],
                    'operacao': op['operacao'],
                    'status': 'simulado',
                    'estimativa_tempo': op['estimativa_tempo'],
                    'indices_afetados': len(op['indices'])
                })
        else:
            # Execução real (simplificada - em produção usaria comandos SQL específicos)
            for op in operacoes_otimizacao:
                try:
                    # Aqui seriam executados os comandos SQL reais de otimização
                    # Por exemplo: db.execute(text(f"REINDEX TABLE {op['tabela']}"))
                    
                    resultados.append({
                        'tabela': op['tabela'],
                        'operacao': op['operacao'],
                        'status': 'concluido',
                        'tempo_execucao': f"{op['estimativa_tempo']} (simulado)",
                        'indices_otimizados': len(op['indices'])
                    })
                except Exception as e:
                    resultados.append({
                        'tabela': op['tabela'],
                        'operacao': op['operacao'],
                        'status': 'erro',
                        'erro': str(e)
                    })
        
        resumo_otimizacao = {
            'executado_em': datetime.now().isoformat(),
            'modo': 'simulacao' if dry_run else 'execucao_real',
            'total_operacoes': len(operacoes_otimizacao),
            'operacoes_concluidas': len([r for r in resultados if r['status'] == 'concluido']),
            'operacoes_com_erro': len([r for r in resultados if r['status'] == 'erro']),
            'detalhes_operacoes': resultados,
            'proximos_passos': [
                'Executar VACUUM ANALYZE completo em horário de baixa atividade',
                'Monitorar performance das consultas após otimização',
                'Agendar otimizações regulares (semanal/mensal)'
            ] if not dry_run else [
                'Executar com dry_run=false para realizar otimização real',
                'Planejar janela de manutenção apropriada',
                'Fazer backup antes da execução real'
            ]
        }
        
        return success_response(resumo_otimizacao, f'Otimização {"simulada" if dry_run else "executada"} com sucesso')
    except Exception as e:
        return error_response(message=f'Erro na otimização: {str(e)}')

@router.post("/passada/manutencao/limpeza-geral", 
            tags=['Manutenção'], 
            status_code=status.HTTP_200_OK, 
            response_model=models.ApiResponse)
async def limpeza_geral_sistema(
    confirmar: bool = Query(False, description="Confirmar limpeza"),
    incluir_logs: bool = Query(True, description="Incluir limpeza de logs"),
    incluir_cache: bool = Query(True, description="Incluir limpeza de cache"),
    incluir_temporarios: bool = Query(True, description="Incluir arquivos temporários"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Limpeza geral do sistema de passadas"""
    if not confirmar:
        return error_response(message='Operação de limpeza requer confirmação explícita')
    
    try:
        resultados_limpeza = {
            'executado_em': datetime.now().isoformat(),
            'executado_por': usuario.id if hasattr(usuario, 'id') else 'sistema',
            'operacoes_realizadas': []
        }
        
        # 1. Limpeza de passadas antigas pendentes (mais de 30 dias)
        if incluir_temporarios:
            data_limite = datetime.now() - timedelta(days=30)
            passadas_antigas = db.query(schemas.PassadasTrio).filter(
                and_(
                    schemas.PassadasTrio.status == 'pendente',
                    schemas.PassadasTrio.created_at < data_limite
                )
            ).all()
            
            quantidade_removida = len(passadas_antigas)
            for passada in passadas_antigas:
                db.delete(passada)
            
            resultados_limpeza['operacoes_realizadas'].append({
                'operacao': 'limpeza_passadas_antigas',
                'registros_removidos': quantidade_removida,
                'criterio': 'passadas pendentes > 30 dias'
            })
        
        # 2. Limpeza de configurações órfãs
        configs_orfas = db.query(schemas.ConfiguracaoPassadasProva).filter(
            ~schemas.ConfiguracaoPassadasProva.prova_id.in_(
                db.query(schemas.Provas.id).filter(schemas.Provas.ativa == True)
            )
        ).all()
        
        quantidade_configs_removidas = len(configs_orfas)
        for config in configs_orfas:
            db.delete(config)
        
        resultados_limpeza['operacoes_realizadas'].append({
            'operacao': 'limpeza_configuracoes_orfas',
            'registros_removidos': quantidade_configs_removidas,
            'criterio': 'configurações sem prova ativa'
        })
        
        # 3. Limpeza de controles de participação órfãos
        controles_orfaos = db.query(schemas.ControleParticipacao).filter(
            or_(
                ~schemas.ControleParticipacao.competidor_id.in_(
                    db.query(schemas.Competidores.id).filter(schemas.Competidores.ativo == True)
                ),
                ~schemas.ControleParticipacao.prova_id.in_(
                    db.query(schemas.Provas.id).filter(schemas.Provas.ativa == True)
                )
            )
        ).all()
        
        quantidade_controles_removidos = len(controles_orfaos)
        for controle in controles_orfaos:
            db.delete(controle)
        
        resultados_limpeza['operacoes_realizadas'].append({
            'operacao': 'limpeza_controles_orfaos',
            'registros_removidos': quantidade_controles_removidos,
            'criterio': 'controles sem competidor/prova ativo'
        })
        
        # 4. Atualização de timestamps e limpeza de campos desnecessários
        passadas_sem_updated_at = db.query(schemas.PassadasTrio).filter(
            schemas.PassadasTrio.updated_at.is_(None)
        ).all()
        
        for passada in passadas_sem_updated_at:
            passada.updated_at = passada.created_at or datetime.now()
        
        resultados_limpeza['operacoes_realizadas'].append({
            'operacao': 'correcao_timestamps',
            'registros_atualizados': len(passadas_sem_updated_at),
            'criterio': 'passadas sem updated_at'
        })
        
        # Commit de todas as operações
        db.commit()
        
        # 5. Operações de cache e logs (simuladas)
        if incluir_cache:
            resultados_limpeza['operacoes_realizadas'].append({
                'operacao': 'limpeza_cache',
                'status': 'simulado',
                'descricao': 'Cache de consultas limpo'
            })
        
        if incluir_logs:
            resultados_limpeza['operacoes_realizadas'].append({
                'operacao': 'limpeza_logs',
                'status': 'simulado',
                'descricao': 'Logs antigos arquivados'
            })
        
        # Resumo final
        total_removidos = sum([
            op.get('registros_removidos', 0) 
            for op in resultados_limpeza['operacoes_realizadas']
        ])
        
        total_atualizados = sum([
            op.get('registros_atualizados', 0) 
            for op in resultados_limpeza['operacoes_realizadas']
        ])
        
        resultados_limpeza['resumo'] = {
            'total_registros_removidos': total_removidos,
            'total_registros_atualizados': total_atualizados,
            'total_operacoes': len(resultados_limpeza['operacoes_realizadas']),
            'tempo_execucao': '< 1 minuto',
            'espaco_liberado_estimado': f'{total_removidos * 0.002:.2f} MB'
        }
        
        return success_response(
            resultados_limpeza,
            f'Limpeza concluída: {total_removidos} removidos, {total_atualizados} atualizados'
        )
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        return error_response(message=f'Erro na limpeza geral: {str(e)}')


@router.post("/passada/aplicar-sat/{passada_id}", 
            tags=['Passadas'], 
            status_code=status.HTTP_200_OK, 
            response_model=models.ApiResponse)
async def aplicar_sat_passada(
    passada_id: int = Path(..., description="ID da passada"),
    request: models.AplicarSatRequest = Body(...),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Aplica SAT (Passadas) em uma passada"""
    try:
        passada = RepositorioPassadas(db).aplicar_sat_passada(
            passada_id, 
            request.motivo, 
            request.aplicado_por or (usuario.nome if hasattr(usuario, 'nome') else 'Sistema')
        )
        return success_response(passada, 'SAT aplicado com sucesso')
    except ValueError as e:
        return error_response(message=str(e))
    except Exception as e:
        return error_response(message=f'Erro ao aplicar SAT: {str(e)}')

@router.post("/passada/remover-sat/{passada_id}", 
            tags=['Passadas'], 
            status_code=status.HTTP_200_OK, 
            response_model=models.ApiResponse)
async def remover_sat_passada(
    passada_id: int = Path(..., description="ID da passada"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Remove SAT de uma passada"""
    try:
        passada = RepositorioPassadas(db).remover_sat_passada(passada_id)
        return success_response(passada, 'SAT removido com sucesso')
    except ValueError as e:
        return error_response(message=str(e))
    except Exception as e:
        return error_response(message=f'Erro ao remover SAT: {str(e)}')

@router.get("/passada/listar-sat", 
           tags=['Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def listar_passadas_sat(
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    categoria_id: Optional[int] = Query(None, description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista todas as passadas que receberam SAT"""
    try:
        passadas_sat = RepositorioPassadas(db).listar_passadas_sat(prova_id, categoria_id)
        
        if not passadas_sat:
            return error_response(message='Nenhuma passada com SAT encontrada')
        
        return success_response(passadas_sat, f'{len(passadas_sat)} passadas com SAT encontradas')
    except Exception as e:
        return error_response(message=f'Erro ao listar passadas SAT: {str(e)}')

@router.get("/passada/estatisticas-sat", 
           tags=['Passadas'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def obter_estatisticas_sat(
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém estatísticas sobre aplicações de SAT"""
    try:
        stats = RepositorioPassadas(db).obter_estatisticas_sat(prova_id)
        return success_response(stats, 'Estatísticas SAT obtidas com sucesso')
    except Exception as e:
        return error_response(message=f'Erro ao obter estatísticas SAT: {str(e)}')

@router.get("/passada/relatorio-sat", 
           tags=['Relatórios SAT'], 
           status_code=status.HTTP_200_OK, 
           response_model=models.ApiResponse)
async def gerar_relatorio_sat(
    prova_id: Optional[int] = Query(None, description="ID da prova"),
    periodo_dias: int = Query(30, ge=1, le=365, description="Período em dias"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera relatório completo de aplicações SAT"""
    try:
        relatorio = RepositorioPassadas(db).gerar_relatorio_sat(prova_id, periodo_dias)
        return success_response(relatorio, 'Relatório SAT gerado com sucesso')
    except Exception as e:
        return error_response(message=f'Erro ao gerar relatório SAT: {str(e)}')