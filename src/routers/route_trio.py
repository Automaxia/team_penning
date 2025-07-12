import traceback
from fastapi import APIRouter, status, Depends, HTTPException, Path, Query, Body
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload, aliased
from sqlalchemy import select, and_, or_, func, outerjoin
from datetime import datetime, date
from src.utils.auth_utils import obter_usuario_logado
from src.database.db import get_db
from src.database import models, schemas
from src.utils.api_response import success_response, error_response
from src.repositorios.trio import RepositorioTrio
from src.repositorios.competidor import RepositorioCompetidor
from src.utils.route_error_handler import RouteErrorHandler

router = APIRouter(route_class=RouteErrorHandler)

# -------------------------- Rotas Básicas de Trios --------------------------
@router.get("/trio/pesquisar", tags=['Trio'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def pesquisar_trios(
    prova_id: Optional[int] = Query(default=None, description="ID da prova"),
    categoria_id: Optional[int] = Query(default=None, description="ID da categoria"), 
    status: Optional[str] = Query(default=None, description="Status do trio"),
    formacao_manual: Optional[bool] = Query(default=None, description="Formação manual"),
    db: Session = Depends(get_db)
):
    """Pesquisa trios com filtros opcionais"""
    
    try:

        subq = (
            db.query(
                schemas.Trios.id.label('trio_id'),
                func.count(schemas.PassadasTrio.id).label('total_passadas')
            )
            .outerjoin(schemas.PassadasTrio, schemas.PassadasTrio.trio_id == schemas.Trios.id)
            .group_by(schemas.Trios.id)
        ).subquery()

        # Alias para o subquery
        sub = aliased(subq)

        # SEMPRE usar query com joinedload para garantir que os relacionamentos sejam carregados
        query = (
            db.query(schemas.Trios).options(
                joinedload(schemas.Trios.integrantes).joinedload(schemas.IntegrantesTrios.competidor),
                joinedload(schemas.Trios.prova),
                joinedload(schemas.Trios.categoria),
                joinedload(schemas.Trios.resultados)
            )
            .outerjoin(sub, sub.c.trio_id == schemas.Trios.id)
        )
        
        # Aplicar filtros
        if prova_id:
            query = query.filter(schemas.Trios.prova_id == prova_id)
        if categoria_id:
            query = query.filter(schemas.Trios.categoria_id == categoria_id)
        if status:
            query = query.filter(schemas.Trios.status == status)
        if formacao_manual is not None:
            query = query.filter(schemas.Trios.formacao_manual == formacao_manual)
            
        # Ordenar e executar
        trios = query.order_by(
            sub.c.total_passadas.asc().nullsfirst(),
            schemas.Trios.categoria_id.asc(),
            schemas.Trios.numero_trio.asc()
        ).all()        
        
        if not trios:
            return error_response(message='Nenhum trio encontrado!')

        trios_serializados = []
        for trio in trios:
            # Função auxiliar para lidar com enum/string de forma segura
            def get_enum_value(field):
                if field is None:
                    return None
                if hasattr(field, 'value'):
                    return field.value
                return str(field)
            
            trio_dict = {
                "id": trio.id,
                "prova_id": trio.prova_id,
                "categoria_id": trio.categoria_id,
                "handicap_total": trio.handicap_total,
                "idade_total": trio.idade_total,
                "status": get_enum_value(trio.status),  # CORREÇÃO: uso seguro
                "is_cabeca_chave": trio.is_cabeca_chave,
                "numero_trio": trio.numero_trio,
                "formacao_manual": trio.formacao_manual,
                "cup_type": get_enum_value(trio.cup_type),  # CORREÇÃO: uso seguro
                "created_at": trio.created_at.isoformat() if trio.created_at else None,
                
                # Serializar prova
                "prova": {
                    "id": trio.prova.id,
                    "nome": trio.prova.nome,
                    "data": trio.prova.data.isoformat() if trio.prova and trio.prova.data else None
                } if trio.prova else None,
                
                # Serializar categoria
                "categoria": {
                    "id": trio.categoria.id,
                    "nome": trio.categoria.nome,
                    "tipo": get_enum_value(trio.categoria.tipo)  # CORREÇÃO: uso seguro
                } if trio.categoria else None,
                
                # Serializar integrantes
                "integrantes": []
            }
            
            # Adicionar integrantes
            for integrante in trio.integrantes:
                # Calcular idade dinamicamente se necessário
                idade_competidor = None
                if integrante.competidor and integrante.competidor.data_nascimento:
                    from datetime import date
                    hoje = date.today()
                    nascimento = integrante.competidor.data_nascimento
                    idade_competidor = hoje.year - nascimento.year
                    if (hoje.month, hoje.day) < (nascimento.month, nascimento.day):
                        idade_competidor -= 1
                elif hasattr(integrante.competidor, 'idade') and integrante.competidor.idade:
                    idade_competidor = integrante.competidor.idade
                
                integrante_dict = {
                    "id": integrante.id,
                    "trio_id": integrante.trio_id,
                    "competidor_id": integrante.competidor_id,
                    "ordem_escolha": integrante.ordem_escolha,
                    "is_cabeca_chave": getattr(integrante, 'is_cabeca_chave', False),  # CORREÇÃO: uso seguro
                    
                    # Dados do competidor
                    "competidor": {
                        "id": integrante.competidor.id,
                        "nome": integrante.competidor.nome,
                        "handicap": integrante.competidor.handicap,
                        "idade": idade_competidor,
                        "sexo": integrante.competidor.sexo,
                        "cidade": getattr(integrante.competidor, 'cidade', None),
                        "estado": getattr(integrante.competidor, 'estado', None),
                        "data_nascimento": integrante.competidor.data_nascimento.isoformat() if integrante.competidor.data_nascimento else None
                    } if integrante.competidor else None
                }
                trio_dict["integrantes"].append(integrante_dict)
            
            # Serializar resultado (se houver)
            if hasattr(trio, 'resultados') and trio.resultados:
                trio_dict["resultado"] = {
                    "id": trio.resultados.id,
                    "colocacao": getattr(trio.resultados, 'colocacao', None),
                    "passada1_tempo": getattr(trio.resultados, 'passada1_tempo', None),
                    "passada2_tempo": getattr(trio.resultados, 'passada2_tempo', None),
                    "media_tempo": getattr(trio.resultados, 'media_tempo', None),
                    "premiacao_valor": getattr(trio.resultados, 'premiacao_valor', None),
                    "no_time": getattr(trio.resultados, 'no_time', False),
                    "observacoes": getattr(trio.resultados, 'observacoes', None)
                }
            else:
                trio_dict["resultado"] = None
            
            trios_serializados.append(trio_dict)
        
        return success_response(trios_serializados, f'Encontrados {len(trios_serializados)} trios')
        
    except Exception as e:
        # Debug detalhado do erro
        import traceback
        print(f"Erro na pesquisa de trios: {str(e)}")
        print("Traceback completo:")
        traceback.print_exc()
        return error_response(message=f'Erro na pesquisa: {str(e)}')

@router.get("/trio/consultar/{trio_id}", tags=['Trio'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def consultar_trio(
    trio_id: int = Path(..., description="ID do trio"),
    db: Session = Depends(get_db)
):
    """Consulta um trio específico com integrantes e resultados"""
    
    trio = await RepositorioTrio(db).get_by_id(trio_id)
    if not trio:
        return error_response(message='Trio não encontrado!')
    
    return success_response(trio)

@router.post("/trio/criar", tags=['Trio'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def criar_trio(
    dados: models.TrioComIntegrantes,
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

@router.get("/trio/proximo-numero/{prova_id}/{categoria_id}", tags=['Trio Utilitários'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def obter_proximo_numero_trio(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Obtém o próximo número disponível para um trio"""
    
    try:
        proximo_numero = await RepositorioTrio(db).get_proximo_numero_trio(prova_id, categoria_id)
        return success_response({
            'proximo_numero': proximo_numero,
            'prova_id': prova_id,
            'categoria_id': categoria_id
        })
    except Exception as e:
        return error_response(message=f'Erro ao obter próximo número: {str(e)}')

@router.put("/trio/atualizar/{trio_id}", tags=['Trio'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def atualizar_trio(
    trio_id: int = Path(..., description="ID do trio"),
    trio_data: models.TrioPUT = Body(...),
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

@router.delete("/trio/deletar/{trio_id}", tags=['Trio'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
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

@router.get("/trio/prova/{prova_id}", tags=['Trio Consulta'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_trios_prova(
    prova_id: int = Path(..., description="ID da prova"),
    db: Session = Depends(get_db)
):
    """Lista todos os trios de uma prova"""
    
    try:
        trios = await RepositorioTrio(db).get_trios_prova(prova_id)
        if not trios:
            return error_response(message='Nenhum trio encontrado para esta prova!')
        
        return success_response(trios, f'Encontrados {len(trios)} trios')
        
    except Exception as e:
        return error_response(message=f'Erro ao listar trios: {str(e)}')

@router.get("/trio/prova/{prova_id}/categoria/{categoria_id}", tags=['Trio Consulta'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_trios_prova_categoria(
    prova_id: int = Path(..., description="ID da prova"),
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista trios de uma prova e categoria específicas"""
    
    try:
        trios = await RepositorioTrio(db).get_by_prova_categoria(prova_id, categoria_id)
        if not trios:
            return error_response(message='Nenhum trio encontrado para esta prova/categoria!')
        
        return success_response(trios, f'Encontrados {len(trios)} trios')
        
    except Exception as e:
        return error_response(message=f'Erro ao listar trios: {str(e)}')

# -------------------------- Sorteios --------------------------

@router.post("/trio/sortear", tags=['Trio Sorteio'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def sortear_trios(
    dados: models.SorteioRequest,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Realiza sorteio de trios baseado nas regras da categoria e configuração de passadas"""
    
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
        print(traceback.format_exc())
        return error_response(message=str(e))

@router.post("/trio/configurar-passadas-sorteio", tags=['Trio Configuração'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def configurar_passadas_para_sorteio(
    prova_id: int = Body(...),
    categoria_id: int = Body(...),
    max_passadas_por_trio: int = Body(...),
    max_corridas_por_pessoa: int = Body(...),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Configura passadas antes de realizar sorteio"""
    
    try:
        from src.repositorios.passadas import RepositorioPassadas
        
        config_data = models.ConfiguracaoPassadasPOST(
            prova_id=prova_id,
            categoria_id=categoria_id,
            max_passadas_por_trio=max_passadas_por_trio,
            max_corridas_por_pessoa=max_corridas_por_pessoa,
            tempo_limite_padrao=60.0,
            intervalo_minimo_passadas=5,
            permite_repetir_boi=False,
            ativa=True
        )
        
        config = RepositorioPassadas(db).criar_configuracao(config_data)
        
        return success_response(
            config,
            'Configuração de passadas criada. Agora você pode realizar o sorteio.',
            status_code=201
        )
        
    except ValueError as e:
        return error_response(message=str(e))

@router.post("/trio/validar-sorteio", tags=['Trio Sorteio'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def validar_sorteio(
    dados: Dict[str, Any] = Body(..., example={
        "prova_id": 1,
        "categoria_id": 1,
        "competidores_ids": [1, 2, 3, 4, 5, 6]
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """
    Valida se é possível realizar sorteio com os competidores informados.
    
    REGRA FUNDAMENTAL CORRIGIDA:
    - Cada trio faz 1 passada (max_passadas_por_trio = 1)
    - Cada competidor deve fazer N passadas (max_corridas_por_pessoa = 6)
    - Logo, cada competidor deve participar de N trios diferentes
    - Total de participações = competidores × passadas_por_competidor
    - Total de trios = total_participações ÷ 3
    """
    
    prova_id = dados.get('prova_id')
    categoria_id = dados.get('categoria_id')
    competidores_ids = dados.get('competidores_ids', [])
    
    if not prova_id or not categoria_id or not competidores_ids:
        return error_response(message='Dados obrigatórios: prova_id, categoria_id e competidores_ids')
    
    try:
        # Verificar categoria
        categoria = db.execute(
            select(schemas.Categorias).where(schemas.Categorias.id == categoria_id)
        ).scalars().first()
        
        if not categoria:
            return error_response(message='Categoria não encontrada!')
        
        if not categoria.permite_sorteio:
            return error_response(message='Esta categoria não permite sorteio!')

        # Buscar configuração de passadas (obrigatória)
        config_passadas = db.execute(
            select(schemas.ConfiguracaoPassadasProva).where(
                schemas.ConfiguracaoPassadasProva.prova_id == prova_id,
                schemas.ConfiguracaoPassadasProva.categoria_id == categoria_id,
                schemas.ConfiguracaoPassadasProva.ativa == True
            )
        ).scalars().first()

        if not config_passadas:
            return error_response(message='Configuração de passadas não encontrada! Configure antes de sortear.')
        
        # PARÂMETROS FUNDAMENTAIS
        passadas_por_competidor = config_passadas.max_corridas_por_pessoa  # Ex: 6 passadas
        passadas_por_trio = config_passadas.max_passadas_por_trio          # Ex: 1 passada
        tamanho_trio = 3
        
        '''print(f"🎯 CONFIGURAÇÃO:")
        print(f"   Passadas por competidor: {passadas_por_competidor}")
        print(f"   Passadas por trio: {passadas_por_trio}")
        print(f"   Cada competidor participará de {passadas_por_competidor // passadas_por_trio} trios diferentes")'''
        
        # Verificar competidores já participando desta prova/categoria
        trios_existentes = db.execute(
            select(schemas.Trios).where(
                schemas.Trios.prova_id == prova_id,
                schemas.Trios.categoria_id == categoria_id
            )
        ).scalars().all()
        
        # Contar participações atuais de cada competidor
        participacoes_atuais = {}
        if trios_existentes:
            integrantes_existentes = db.execute(
                select(schemas.IntegrantesTrios.competidor_id, func.count().label('total')).where(
                    schemas.IntegrantesTrios.trio_id.in_([t.id for t in trios_existentes])
                ).group_by(schemas.IntegrantesTrios.competidor_id)
            ).all()
            
            participacoes_atuais = {int(row.competidor_id): int(row.total) for row in integrantes_existentes}
        
        print(f"🔍 PARTICIPAÇÕES ATUAIS:")
        for comp_id, participacoes in participacoes_atuais.items():
            print(f"   Competidor {comp_id}: {participacoes} trios")
        
        # Verificar elegibilidade dos competidores
        competidores_aptos = []
        competidores_bloqueados = []
        participacoes_disponiveis_total = 0
        
        for competidor_id in competidores_ids:
            # Verificar se competidor existe
            competidor = db.execute(
                select(schemas.Competidores).where(
                    schemas.Competidores.id == competidor_id,
                    schemas.Competidores.ativo == True
                )
            ).scalars().first()
            
            if not competidor:
                competidores_bloqueados.append({
                    'competidor_id': competidor_id,
                    'motivo': 'Competidor não encontrado ou inativo'
                })
                continue
            
            # Calcular participações restantes
            participacoes_feitas = participacoes_atuais.get(competidor_id, 0)
            participacoes_restantes = passadas_por_competidor - participacoes_feitas
            
            # Verificar controle de participação
            controle = db.execute(
                select(schemas.ControleParticipacao).where(
                    schemas.ControleParticipacao.competidor_id == competidor_id,
                    schemas.ControleParticipacao.prova_id == prova_id,
                    schemas.ControleParticipacao.categoria_id == categoria_id
                )
            ).scalars().first()
            
            bloqueado = False
            motivo_bloqueio = None
            
            # Verificar se está bloqueado no controle
            '''if controle and not controle.pode_competir:
                bloqueado = True
                motivo_bloqueio = controle.motivo_bloqueio or 'Bloqueado no controle de participação'
            
            # Verificar se já atingiu limite de participações
            elif participacoes_restantes <= 0:
                bloqueado = True
                motivo_bloqueio = f'Já atingiu o limite de {passadas_por_competidor} participações'''''
            
            if bloqueado:
                competidores_bloqueados.append({
                    'competidor_id': competidor_id,
                    'nome': competidor.nome,
                    'participacoes_feitas': participacoes_feitas,
                    'motivo': motivo_bloqueio
                })
            else:
                competidores_aptos.append({
                    'competidor_id': competidor_id,
                    'nome': competidor.nome,
                    'handicap': competidor.handicap,
                    'idade': competidor.idade,
                    'sexo': competidor.sexo,
                    'participacoes_feitas': participacoes_feitas,
                    'participacoes_restantes': participacoes_restantes,
                    'status': 'NOVO' if participacoes_feitas == 0 else 'ATIVO'
                })
                participacoes_disponiveis_total += participacoes_restantes
        
        '''print(f"📊 ANÁLISE DE ELEGIBILIDADE:")
        print(f"   Competidores aptos: {len(competidores_aptos)}")
        print(f"   Competidores bloqueados: {len(competidores_bloqueados)}")
        print(f"   Participações disponíveis total: {participacoes_disponiveis_total}")'''
        
        # CÁLCULO CORRETO: Total de trios baseado em participações disponíveis
        max_trios_possiveis = participacoes_disponiveis_total // tamanho_trio
        participacoes_sobrando = participacoes_disponiveis_total % tamanho_trio

        observacoes = []
        total_competidores = len(competidores_aptos)
        passadas_originais = passadas_por_competidor

        # Encontrar o número de passadas que resulte em divisão exata por 3
        passadas_testadas = []
        for passadas_teste in range(1, passadas_originais + 3):  # Testar até 2 passadas extras
            participacoes_totais = total_competidores * passadas_teste
            resto = participacoes_totais % tamanho_trio
            trios_possiveis = participacoes_totais // tamanho_trio
            
            passadas_testadas.append({
                'passadas': passadas_teste,
                'participacoes_totais': participacoes_totais,
                'trios_possiveis': trios_possiveis,
                'resto': resto,
                'perfeito': resto == 0
            })
            
            print(f"   Teste {passadas_teste} passadas: {participacoes_totais} participações = {trios_possiveis} trios (resto: {resto})")

        # Priorizar a configuração original se ela funciona
        passadas_ideais = passadas_originais
        melhor_opcao = None

        # Primeiro, verificar se as passadas originais funcionam
        for teste in passadas_testadas:
            if teste['passadas'] == passadas_originais and teste['resto'] == 0:
                melhor_opcao = teste
                print(f"✅ Configuração original ({passadas_originais} passadas) é perfeita!")
                break

        # Se não funciona, buscar a melhor alternativa
        if not melhor_opcao:
            # Priorizar: 1) Resto = 0, 2) Menor diferença da configuração original
            opcoes_perfeitas = [t for t in passadas_testadas if t['resto'] == 0]
            
            if opcoes_perfeitas:
                # Escolher a mais próxima da configuração original
                melhor_opcao = min(opcoes_perfeitas, 
                                key=lambda x: abs(x['passadas'] - passadas_originais))
                print(f"✅ Melhor alternativa: {melhor_opcao['passadas']} passadas (resto 0)")
            else:
                # Se nenhuma opção é perfeita, escolher a com menor resto
                melhor_opcao = min(passadas_testadas, key=lambda x: x['resto'])
                print(f"⚠️ Nenhuma opção perfeita. Melhor: {melhor_opcao['passadas']} passadas (resto: {melhor_opcao['resto']})")

        # Aplicar a configuração ideal
        passadas_por_competidor = melhor_opcao['passadas']
        participacoes_disponiveis_total = melhor_opcao['participacoes_totais']
        max_trios_possiveis = melhor_opcao['trios_possiveis']
        participacoes_sobrando = melhor_opcao['resto']

        # Adicionar observações sobre o ajuste
        if passadas_por_competidor != passadas_originais:
            if passadas_por_competidor < passadas_originais:
                observacoes.append(f'Passadas reduzidas de {passadas_originais} para {passadas_por_competidor} para balancear perfeitamente')
            else:
                observacoes.append(f'Passadas aumentadas de {passadas_originais} para {passadas_por_competidor} para balancear perfeitamente')
        else:
            observacoes.append(f'Configuração original de {passadas_por_competidor} passadas já está balanceada')

        # Recalcular estatísticas dos competidores aptos com as novas passadas
        for competidor in competidores_aptos:
            competidor['participacoes_restantes'] = passadas_por_competidor - competidor['participacoes_feitas']
        
        print(f"🧮 CÁLCULO DE TRIOS:")
        print(f"   {participacoes_disponiveis_total} participações ÷ {tamanho_trio} = {max_trios_possiveis} trios")
        print(f"   Participações que sobram: {participacoes_sobrando}")
        
        # Validações específicas por categoria
        trios_finais_possiveis = max_trios_possiveis
        observacoes = []
        competidores_para_sorteio = competidores_aptos.copy()
        
        # Validação para categorias com limite de participantes no sorteio
        if categoria.tipo in ['kids', 'feminina']:
            min_sorteio = categoria.min_inscricoes_sorteio or 3
            max_sorteio = categoria.max_inscricoes_sorteio or 9
            
            total_competidores_aptos = len(competidores_aptos)
            
            if total_competidores_aptos < min_sorteio:
                return error_response(
                    message=f'Mínimo de {min_sorteio} competidores aptos necessários para sorteio. Encontrados: {total_competidores_aptos}'
                )
            
            # Para kids/feminina, limitar o número de competidores sorteados
            if total_competidores_aptos > max_sorteio:
                # Sortear apenas max_sorteio competidores
                import random
                competidores_para_sorteio = random.sample(competidores_aptos, max_sorteio)
                participacoes_limitadas = sum(comp['participacoes_restantes'] for comp in competidores_para_sorteio)
                trios_finais_possiveis = participacoes_limitadas // tamanho_trio
                observacoes.append(f'Apenas {max_sorteio} competidores serão sorteados (máximo da categoria)')
            
            observacoes.append(f'Categoria {categoria.tipo}: {len(competidores_para_sorteio)} competidores participarão do sorteio')
        
        # Validação para categoria feminina (apenas mulheres)
        if categoria.tipo == 'feminina':
            mulheres_aptas = [comp for comp in competidores_para_sorteio if comp.get('sexo') == 'F']
            if len(mulheres_aptas) < len(competidores_para_sorteio):
                competidores_para_sorteio = mulheres_aptas
                participacoes_femininas = sum(comp['participacoes_restantes'] for comp in mulheres_aptas)
                trios_finais_possiveis = participacoes_femininas // tamanho_trio
                observacoes.append('Apenas competidoras do sexo feminino podem participar desta categoria')
        
        # Validação para categoria mirim (limite de idade por trio)
        if categoria.tipo == 'mirim' and categoria.idade_max_trio:
            observacoes.append(f'Será respeitado limite de {categoria.idade_max_trio} anos por trio (pode reduzir número de trios possíveis)')
        
        # Validação para categoria handicap (limite de handicap por trio)
        if categoria.tipo == 'handicap' and categoria.handicap_max_trio:
            observacoes.append(f'Será respeitado limite de handicap {categoria.handicap_max_trio} por trio (pode reduzir número de trios possíveis)')
        
        # Construir resposta de validação (MANTENDO NOMES ORIGINAIS)
        validacao = {
            'valido': trios_finais_possiveis > 0,
            'total_competidores': len(competidores_ids),
            'competidores_aptos': len(competidores_aptos),
            'participacoes_por_competidor': passadas_por_competidor,
            'participacoes_por_competidor_original': passadas_originais,
            'passadas_ajustadas': passadas_por_competidor != passadas_originais,
            'total_participacoes_teoricas': len(competidores_aptos) * passadas_por_competidor,
            'total_participacoes_disponiveis': participacoes_disponiveis_total,
            'max_trios_teoricos': (len(competidores_aptos) * passadas_por_competidor) // tamanho_trio,
            'max_trios_possiveis': trios_finais_possiveis,
            'participacoes_sobrando': participacoes_sobrando,
            'categoria_tipo': categoria.tipo,
            'permite_sorteio': categoria.permite_sorteio,
            'configuracao': {
                'max_passadas_por_trio': config_passadas.max_passadas_por_trio,
                'max_corridas_por_pessoa': config_passadas.max_corridas_por_pessoa
            },
            'observacoes': observacoes
        }
        
        # Adicionar observações explicativas
        validacao['observacoes'].append(
            f'Cada competidor participará de {passadas_por_competidor // passadas_por_trio} trios diferentes para completar {passadas_por_competidor} passadas'
        )
        
        if len(competidores_bloqueados) > 0:
            validacao['observacoes'].append(
                f'{len(competidores_bloqueados)} competidor(es) estão bloqueados ou já atingiram o limite'
            )
        
        if participacoes_sobrando > 0:
            validacao['observacoes'].append(
                f'{participacoes_sobrando} participação(ões) não serão utilizadas (não formam trio completo)'
            )
        
        # Validação final
        if trios_finais_possiveis == 0:
            validacao['valido'] = False
            if len(competidores_aptos) == 0:
                validacao['observacoes'].append('Nenhum competidor apto disponível')
            elif participacoes_disponiveis_total < tamanho_trio:
                validacao['observacoes'].append(
                    f'Participações insuficientes ({participacoes_disponiveis_total}) para formar ao menos 1 trio (mínimo {tamanho_trio})'
                )
            else:
                validacao['observacoes'].append('Nenhum trio pode ser formado devido às restrições da categoria')
        
        # Adicionar exemplo prático genérico
        if trios_finais_possiveis > 0:
            competidores_unicos = len(set(comp['competidor_id'] for comp in competidores_para_sorteio))
            media_participacoes = participacoes_disponiveis_total / competidores_unicos if competidores_unicos > 0 else 0
            
            validacao['exemplo_pratico'] = {
                'trios_formados': trios_finais_possiveis,
                'competidores_participantes': competidores_unicos,
                'media_participacoes_por_competidor': round(media_participacoes, 1),
                'total_passadas_prova': trios_finais_possiveis * passadas_por_trio,
                'explicacao': f'Serão formados {trios_finais_possiveis} trios, com cada competidor participando em média de {round(media_participacoes, 1)} trios'
            }
            
            # Exemplo genérico com cálculo detalhado
            total_competidores_aptos = len(competidores_aptos)
            if total_competidores_aptos > 0:
                validacao['exemplo'] = {
                    'calculo': f'{total_competidores_aptos} competidores × {passadas_por_competidor} participações = {total_competidores_aptos * passadas_por_competidor} participações totais',
                    'resultado': f'{participacoes_disponiveis_total} participações ÷ 3 = {trios_finais_possiveis} trios possíveis',
                    'distribuicao': f'Cada competidor participará de {passadas_por_competidor} trios diferentes (se não houver limitações)'
                }
        
        print(f"✅ VALIDAÇÃO CONCLUÍDA:")
        print(f"   Válido: {validacao['valido']}")
        print(f"   Trios possíveis: {trios_finais_possiveis}")
        print(f"   Participações totais: {participacoes_disponiveis_total}")
        print(f"   Observações: {len(validacao['observacoes'])}")
        
        return success_response(validacao)
        
    except Exception as e:
        print(f"❌ ERRO na validação: {str(e)}")
        print(traceback.format_exc())
        return error_response(message=f'Erro na validação: {str(e)}')
# -------------------------- Copa dos Campeões --------------------------

@router.post("/trio/copa-campeoes", tags=['Trio Copa'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
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

@router.get("/trio/campeoes-elegiveis", tags=['Trio Copa'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
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

@router.get("/trio/estatisticas/{trio_id}", tags=['Trio Estatísticas'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
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

@router.get("/trio/ranking/categoria/{categoria_id}", tags=['Trio Ranking'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
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

@router.post("/trio/validar-inscricao", tags=['Trio Validação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
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

@router.post("/trio/criar-multiplos", tags=['Trio Lote'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
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

@router.put("/trio/reorganizar-numeros/{prova_id}/{categoria_id}", tags=['Trio Lote'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
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

@router.get("/trio/relatorio/participacao-prova/{prova_id}", tags=['Trio Relatórios'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
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

@router.get("/trio/relatorio/formacao-tipos", tags=['Trio Relatórios'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def relatorio_tipos_formacao(
    prova_id: Optional[int] = Query(default=None, description="ID da prova (opcional)"),
    categoria_id: Optional[int] = Query(default=None, description="ID da categoria (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera relatório dos tipos de formação de trios"""
    
    try:
        query = db.query(schemas.Trios)
        
        if prova_id:
            query = query.filter(schemas.Trios.prova_id == prova_id)
        if categoria_id:
            query = query.filter(schemas.Trios.categoria_id == categoria_id)
        
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

@router.get("/trio/exportar", tags=['Trio Exportação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
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

@router.get("/trio/verificar-disponibilidade", tags=['Trio Utilitários'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
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
            inscricao = db.execute(
                select(schemas.IntegrantesTrios).join(
                    schemas.Trios
                ).where(
                    schemas.Trios.prova_id == prova_id,
                    schemas.Trios.categoria_id == categoria_id,
                    schemas.IntegrantesTrios.competidor_id == comp_id
                )
            ).scalars().first()
            
            disponibilidade[comp_id] = {
                'disponivel': inscricao is None,
                'inscrito_trio_id': inscricao.trio_id if inscricao else None
            }
        
        return success_response(disponibilidade)
        
    except Exception as e:
        return error_response(message=f'Erro ao verificar disponibilidade: {str(e)}')

@router.get("/trio/sugestoes-completar", tags=['Trio Utilitários'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
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