from fastapi import APIRouter, status, Depends, HTTPException, Path, Query, Body
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, date
from src.utils.auth_utils import obter_usuario_logado
from src.database.db import get_db
from src.database import models, schemas
from src.utils.api_response import success_response, error_response
from src.repositorios.categoria import RepositorioCategoria
from src.utils.route_error_handler import RouteErrorHandler

router = APIRouter(route_class=RouteErrorHandler)

# -------------------------- Operações Básicas CRUD --------------------------

@router.get("/categoria/listar", tags=['Categoria'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_categorias(
    ativas_apenas: bool = Query(default=True, description="Listar apenas categorias ativas"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista todas as categorias do sistema"""
    
    categorias = await RepositorioCategoria(db).get_all(ativas_apenas)
    if not categorias:
        return error_response(message='Nenhuma categoria encontrada!')
    
    return success_response(categorias, f'{len(categorias)} categorias encontradas')

@router.get("/categoria/consultar/{categoria_id}", tags=['Categoria'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def consultar_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Consulta uma categoria específica pelo ID"""
    
    categoria = await RepositorioCategoria(db).get_by_id(categoria_id)
    if not categoria:
        return error_response(message='Categoria não encontrada!')
    
    return success_response(categoria)

@router.post("/categoria/criar", tags=['Categoria'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def criar_categoria(
    categoria_data: models.CategoriaPOST,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Cria uma nova categoria"""
    
    try:
        categoria = await RepositorioCategoria(db).post(categoria_data)
        return success_response(categoria, 'Categoria criada com sucesso', status_code=201)
    except ValueError as e:
        return error_response(message=str(e))

@router.put("/categoria/atualizar/{categoria_id}", tags=['Categoria'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def atualizar_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    categoria_data: models.CategoriaPUT = Body(...),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Atualiza uma categoria existente"""
    
    try:
        categoria = await RepositorioCategoria(db).put(categoria_id, categoria_data)
        if not categoria:
            return error_response(message='Categoria não encontrada!')
        
        return success_response(categoria, 'Categoria atualizada com sucesso')
    except ValueError as e:
        return error_response(message=str(e))

@router.delete("/categoria/deletar/{categoria_id}", tags=['Categoria'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def excluir_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Remove uma categoria (soft delete se tem trios associados)"""
    
    try:
        sucesso = await RepositorioCategoria(db).delete(categoria_id)
        if sucesso:
            return success_response(None, 'Categoria removida com sucesso')
        else:
            return error_response(message='Erro ao remover categoria')
    except ValueError as e:
        return error_response(message=str(e))

# -------------------------- Consultas por Tipo --------------------------

@router.get("/categoria/tipo/{tipo_categoria}", tags=['Categoria Consulta'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_por_tipo(
    tipo_categoria: schemas.TipoCategoria = Path(..., description="Tipo da categoria"),
    ativas_apenas: bool = Query(default=True, description="Apenas categorias ativas"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista categorias de um tipo específico"""
    
    categorias = await RepositorioCategoria(db).get_by_tipo(tipo_categoria, ativas_apenas)
    if not categorias:
        return error_response(message=f'Nenhuma categoria do tipo {tipo_categoria.value} encontrada!')
    
    return success_response(categorias, f'{len(categorias)} categorias do tipo {tipo_categoria.value}')

@router.get("/categoria/nome/{nome}", tags=['Categoria Consulta'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def buscar_por_nome(
    nome: str = Path(..., description="Nome da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Busca categoria por nome (busca parcial)"""
    
    categoria = await RepositorioCategoria(db).get_by_nome(nome)
    if not categoria:
        return error_response(message=f'Categoria com nome "{nome}" não encontrada!')
    
    return success_response(categoria)

@router.get("/categoria/sorteio", tags=['Categoria Consulta'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def categorias_com_sorteio(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista categorias que permitem sorteio"""
    
    categorias = await RepositorioCategoria(db).get_categorias_que_permitem_sorteio()
    if not categorias:
        return error_response(message='Nenhuma categoria permite sorteio!')
    
    return success_response(categorias, f'{len(categorias)} categorias permitem sorteio')

# -------------------------- Validações --------------------------

@router.post("/categoria/validar-trio", tags=['Categoria Validação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def validar_trio_categoria(
    dados: Dict[str, Any] = Body(..., example={
        "categoria_id": 1,
        "competidores_ids": [1, 2, 3]
    }),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Valida se um trio pode participar de uma categoria"""
    
    categoria_id = dados.get('categoria_id')
    competidores_ids = dados.get('competidores_ids', [])
    
    if not categoria_id or len(competidores_ids) != 3:
        return error_response(message='Deve informar categoria_id e exatamente 3 competidores')
    
    try:
        valido, mensagem = await RepositorioCategoria(db).validar_trio_categoria(competidores_ids, categoria_id)
        
        return success_response({
            'valido': valido,
            'mensagem': mensagem,
            'categoria_id': categoria_id,
            'competidores_ids': competidores_ids
        })
    except Exception as e:
        return error_response(message=f'Erro na validação: {str(e)}')

@router.get("/categoria/competidor/{competidor_id}", tags=['Categoria Validação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def categorias_do_competidor(
    competidor_id: int = Path(..., description="ID do competidor"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista categorias nas quais um competidor pode participar"""
    
    categorias = await RepositorioCategoria(db).get_categorias_competidor(competidor_id)
    if not categorias:
        return error_response(message='Nenhuma categoria disponível para este competidor!')
    
    return success_response(categorias, f'{len(categorias)} categorias disponíveis')

# -------------------------- Estatísticas e Relatórios --------------------------

@router.get("/categoria/estatisticas/{categoria_id}", tags=['Categoria Estatísticas'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def estatisticas_categoria(
    categoria_id: int = Path(..., description="ID da categoria"),
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera estatísticas detalhadas de uma categoria"""
    
    estatisticas = await RepositorioCategoria(db).get_estatisticas_categoria(categoria_id, ano)
    if not estatisticas:
        return error_response(message='Categoria não encontrada ou sem dados!')
    
    return success_response(estatisticas)

@router.get("/categoria/relatorio/participacao", tags=['Categoria Relatórios'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def relatorio_participacao_categorias(
    ano: Optional[int] = Query(default=None, description="Ano específico (opcional)"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Gera relatório de participação por categoria"""
    
    try:
        relatorio = await RepositorioCategoria(db).gerar_relatorio_participacao(ano)
        return success_response(relatorio)
    except Exception as e:
        return error_response(message=f'Erro ao gerar relatório: {str(e)}')

@router.get("/categoria/prova/{prova_id}", tags=['Categoria Consulta'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def categorias_por_prova(
    prova_id: int = Path(..., description="ID da prova"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista categorias de uma prova com estatísticas"""
    
    categorias = await RepositorioCategoria(db).get_categorias_por_prova(prova_id)
    if not categorias:
        return error_response(message='Nenhuma categoria encontrada para esta prova!')
    
    return success_response(categorias)

# -------------------------- Configuração e Exportação --------------------------

@router.get("/categoria/exportar", tags=['Categoria Exportação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def exportar_configuracao_categorias(
    formato: str = Query(default="json", regex="^(json|csv)$", description="Formato de exportação"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Exporta configuração de todas as categorias"""
    
    try:
        dados = await RepositorioCategoria(db).exportar_configuracao_categorias()
        
        return success_response({
            'formato': formato,
            'total_categorias': len(dados),
            'dados': dados,
            'exportado_em': datetime.now().isoformat()
        })
    except Exception as e:
        return error_response(message=f'Erro na exportação: {str(e)}')

@router.post("/categoria/importar", tags=['Categoria Importação'], status_code=status.HTTP_201_CREATED, response_model=models.ApiResponse)
async def importar_categorias(
    categorias_data: List[models.CategoriaPOST] = Body(...),
    sobrescrever: bool = Query(default=False, description="Sobrescrever categorias existentes"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Importa configuração de categorias em lote"""
    
    try:
        repo = RepositorioCategoria(db)
        categorias_criadas = []
        categorias_atualizadas = []
        erros = []
        
        for categoria_data in categorias_data:
            try:
                # Verificar se já existe
                categoria_existente = await repo.get_by_nome(categoria_data.nome)
                
                if categoria_existente and sobrescrever:
                    # Atualizar existente
                    categoria_put = models.CategoriaPUT(
                        nome=categoria_data.nome,
                        tipo=categoria_data.tipo,
                        descricao=categoria_data.descricao,
                        handicap_max_trio=categoria_data.handicap_max_trio,
                        idade_max_trio=categoria_data.idade_max_trio,
                        idade_min_individual=categoria_data.idade_min_individual,
                        idade_max_individual=categoria_data.idade_max_individual,
                        permite_sorteio=categoria_data.permite_sorteio,
                        min_inscricoes_sorteio=categoria_data.min_inscricoes_sorteio,
                        max_inscricoes_sorteio=categoria_data.max_inscricoes_sorteio,
                        sorteio_completo=categoria_data.sorteio_completo,
                        tipo_pontuacao=categoria_data.tipo_pontuacao,
                        ativa=categoria_data.ativa
                    )
                    categoria_atualizada = await repo.put(categoria_existente.id, categoria_put)
                    categorias_atualizadas.append(categoria_atualizada)
                elif not categoria_existente:
                    # Criar nova
                    categoria_criada = await repo.post(categoria_data)
                    categorias_criadas.append(categoria_criada)
                else:
                    erros.append(f"Categoria '{categoria_data.nome}' já existe")
                    
            except Exception as e:
                erros.append(f"Erro ao processar categoria '{categoria_data.nome}': {str(e)}")
        
        return success_response({
            'categorias_criadas': len(categorias_criadas),
            'categorias_atualizadas': len(categorias_atualizadas),
            'erros': erros,
            'dados': {
                'criadas': categorias_criadas,
                'atualizadas': categorias_atualizadas
            }
        }, f'Importação concluída: {len(categorias_criadas)} criadas, {len(categorias_atualizadas)} atualizadas', status_code=201)
        
    except Exception as e:
        return error_response(message=f'Erro na importação: {str(e)}')

# -------------------------- Utilitários --------------------------

@router.get("/categoria/tipos", tags=['Categoria Utilitários'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def listar_tipos_categoria(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Lista todos os tipos de categoria disponíveis"""
    
    tipos = [
        {
            'valor': tipo.value,
            'nome': tipo.name,
            'descricao': _get_descricao_tipo(tipo)
        }
        for tipo in schemas.TipoCategoria
    ]
    
    return success_response(tipos, 'Tipos de categoria disponíveis')

@router.get("/categoria/regras/{tipo_categoria}", tags=['Categoria Utilitários'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def regras_por_tipo(
    tipo_categoria: schemas.TipoCategoria = Path(..., description="Tipo da categoria"),
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna as regras padrão para um tipo de categoria"""
    
    from src.utils.config_lctp import ConfigLCTP
    
    regras = ConfigLCTP.REGRAS_CATEGORIAS.get(tipo_categoria.value, {})
    
    if not regras:
        return error_response(message='Tipo de categoria não possui regras definidas')
    
    return success_response({
        'tipo': tipo_categoria.value,
        'regras': regras,
        'descricao': _get_descricao_tipo(tipo_categoria)
    })

@router.post("/categoria/validar-regras", tags=['Categoria Validação'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def validar_regras_categoria(
    categoria_data: models.CategoriaPOST,
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Valida as regras de uma categoria sem salvá-la"""
    
    try:
        repo = RepositorioCategoria(db)
        await repo._validar_regras_categoria(categoria_data)
        
        return success_response({
            'valido': True,
            'categoria': categoria_data.model_dump(),
            'mensagem': 'Regras da categoria são válidas'
        })
    except Exception as e:
        return success_response({
            'valido': False,
            'categoria': categoria_data.model_dump(),
            'mensagem': str(e)
        })

@router.get("/categoria/resumo", tags=['Categoria Estatísticas'], status_code=status.HTTP_200_OK, response_model=models.ApiResponse)
async def resumo_categorias(
    db: Session = Depends(get_db),
    usuario = Depends(obter_usuario_logado)
):
    """Retorna resumo geral das categorias do sistema"""
    
    try:
        repo = RepositorioCategoria(db)
        todas_categorias = await repo.get_all(ativas_apenas=False)
        
        # Estatísticas básicas
        total_categorias = len(todas_categorias)
        ativas = len([c for c in todas_categorias if c.ativa])
        inativas = total_categorias - ativas
        
        # Por tipo
        por_tipo = {}
        for categoria in todas_categorias:
            tipo = categoria.tipo.value
            if tipo not in por_tipo:
                por_tipo[tipo] = {'total': 0, 'ativas': 0}
            por_tipo[tipo]['total'] += 1
            if categoria.ativa:
                por_tipo[tipo]['ativas'] += 1
        
        # Categorias com sorteio
        com_sorteio = len([c for c in todas_categorias if c.permite_sorteio and c.ativa])
        
        resumo = {
            'total_categorias': total_categorias,
            'ativas': ativas,
            'inativas': inativas,
            'com_sorteio': com_sorteio,
            'por_tipo': por_tipo,
            'tipos_disponiveis': len(schemas.TipoCategoria)
        }
        
        return success_response(resumo)
    except Exception as e:
        return error_response(message=f'Erro ao gerar resumo: {str(e)}')

# -------------------------- Funções Auxiliares --------------------------

def _get_descricao_tipo(tipo: schemas.TipoCategoria) -> str:
    """Retorna descrição do tipo de categoria"""
    descricoes = {
        schemas.TipoCategoria.BABY: "Categoria para crianças até 12 anos com sorteio completo",
        schemas.TipoCategoria.KIDS: "Categoria para jovens de 13 a 17 anos com sorteio parcial",
        schemas.TipoCategoria.MIRIM: "Categoria com limite de idade total por trio (máx 36 anos)",
        schemas.TipoCategoria.FEMININA: "Categoria exclusiva para mulheres",
        schemas.TipoCategoria.ABERTA: "Categoria sem restrições de idade ou handicap",
        schemas.TipoCategoria.SOMA11: "Categoria com limite de handicap total por trio"
    }
    return descricoes.get(tipo, "Descrição não disponível")