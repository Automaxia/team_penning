from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import uvicorn
import logging
from datetime import datetime
from src.utils.exceptions_lctp import LCTPException

# Imports do banco de dados
from src.database.db import get_db, engine, Base
from src.database import schemas, models

# Imports das rotas LCTP
from src.routers import (
    route_competidor, 
    route_trio, 
    route_categoria, 
    route_prova, 
    route_resultado, 
    route_pontuacao,
    route_passadas,
    route_auth,
    route_usuario,
    route_dashboard
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===================================================================
# CONFIGURAÇÃO DE TAGS PARA DOCUMENTAÇÃO
# ===================================================================

tags_metadata = [
    # Competidores
    {
        "name": "Competidor",
        "description": "Gerencia competidores de team penning. Inclui criação, atualização, ranking e estatísticas.",
        "externalDocs": {
            "description": "Regulamento LCTP",
            "url": "https://lctp.com.br/regulamento",
        },
    },
    {
        "name": "Competidor Ranking", 
        "description": "Rankings e estatísticas de competidores por categoria e período."
    },
    {
        "name": "Competidor Trio",
        "description": "Operações relacionadas à formação de trios e validações de regras."
    },
    {
        "name": "Competidor Relatórios",
        "description": "Relatórios de participação e performance dos competidores."
    },
    {
        "name": "Competidor Lote",
        "description": "Operações em lote para múltiplos competidores (importação/exportação)."
    },
    {
        "name": "Competidor Estatísticas",
        "description": "Estatísticas gerais e análises do sistema de competidores."
    },
    {
        "name": "Competidor Exportação",
        "description": "Exportação de dados de competidores em diferentes formatos (JSON/CSV)."
    },
    {
        "name": "Competidor Importação", 
        "description": "Importação de dados de competidores em lote."
    },
    {
        "name": "Competidor Apoio",
        "description": "Funcionalidades auxiliares e listas de opções para competidores."
    },
    
    # Trios
    {
        "name": "Trio",
        "description": "Gerencia trios de competidores. Inclui criação, consulta e validações de regras LCTP."
    },
    {
        "name": "Trio Consulta",
        "description": "Consultas específicas de trios por prova e categoria."
    },
    {
        "name": "Trio Sorteio",
        "description": "Sistema de sorteios automáticos baseado em regras específicas de cada categoria."
    },
    {
        "name": "Trio Copa",
        "description": "Gestão de trios para Copa dos Campeões com sistema de cabeças de chave."
    },
    {
        "name": "Trio Estatísticas",
        "description": "Estatísticas e análises de performance de trios."
    },
    {
        "name": "Trio Ranking",
        "description": "Rankings de trios por categoria e período específico."
    },
    {
        "name": "Trio Validação",
        "description": "Validações de regras para formação de trios (handicap, idade, etc.)."
    },
    {
        "name": "Trio Lote",
        "description": "Operações em lote para criação e atualização de múltiplos trios."
    },
    {
        "name": "Trio Relatórios",
        "description": "Relatórios de participação e tipos de formação de trios."
    },
    {
        "name": "Trio Exportação",
        "description": "Exportação de dados de trios em formatos estruturados."
    },
    {
        "name": "Trio Utilitários", 
        "description": "Utilitários para verificações, sugestões e reorganização de trios."
    },
    
    # Categorias
    {
        "name": "Categoria",
        "description": "Gerencia categorias de competição com suas regras específicas (Baby, Kids, Mirim, Feminina, Aberta, Handicap)."
    },
    {
        "name": "Categoria Consulta",
        "description": "Consultas e filtros específicos de categorias."
    },
    {
        "name": "Categoria Validação",
        "description": "Validações de regras e elegibilidade para categorias."
    },
    {
        "name": "Categoria Estatísticas",
        "description": "Estatísticas de uso e performance das categorias."
    },
    {
        "name": "Categoria Relatórios",
        "description": "Relatórios de participação e análises por categoria."
    },
    {
        "name": "Categoria Exportação",
        "description": "Exportação de configurações e dados de categorias."
    },
    {
        "name": "Categoria Importação",
        "description": "Importação e configuração em lote de categorias."
    },
    {
        "name": "Categoria Utilitários",
        "description": "Utilitários para configuração e validação de categorias."
    },
    
    # Provas
    {
        "name": "Prova",
        "description": "Gerencia provas/eventos de team penning com informações de local, data e configurações."
    },
    {
        "name": "Prova Consulta",
        "description": "Consultas específicas de provas por período, rancho, estado, etc."
    },
    {
        "name": "Prova Estatísticas",
        "description": "Estatísticas de participação e performance das provas."
    },
    {
        "name": "Prova Ranking",
        "description": "Rankings e classificações de provas específicas."
    },
    {
        "name": "Prova Relatórios",
        "description": "Relatórios anuais e análises de provas."
    },
    {
        "name": "Prova Calendário",
        "description": "Gestão do calendário anual de provas."
    },
    {
        "name": "Prova Validação",
        "description": "Validações de data, conflitos e adequação de provas."
    },
    {
        "name": "Prova Utilitários",
        "description": "Utilitários para duplicação, sugestões e configurações."
    },
    {
        "name": "Prova Exportação",
        "description": "Exportação de dados de provas e estatísticas."
    },
    {
        "name": "Prova Importação",
        "description": "Importação de provas em lote."
    },
    {
        "name": "Prova Resumo",
        "description": "Resumos e visões gerais do sistema de provas."
    },
    {
        "name": "Prova Análise",
        "description": "Análises avançadas de frequência e padrões de provas."
    },
    {
        "name": "Prova Configuração",
        "description": "Configurações padrão e templates para provas."
    },
    {
        "name": "Prova Dashboard",
        "description": "Dashboard com visão geral das provas."
    },
    {
        "name": "Prova Métricas",
        "description": "Métricas de performance do sistema de provas."
    },
    {
        "name": "Passadas",
        "description": "🆕 Sistema de controle de passadas múltiplas por trio. Permite que cada trio compita várias vezes respeitando limites por competidor."
    },
    {
        "name": "Passadas Lote",
        "description": "Criação e gerenciamento de múltiplas passadas em lote para otimizar o processo."
    },
    {
        "name": "Passadas Execução",
        "description": "Registro de tempos e execução de passadas com validações automáticas."
    },
    {
        "name": "Passadas Validação",
        "description": "Validações de regras para execução de passadas (limites, intervalos, bois disponíveis)."
    },
    {
        "name": "Configuração Passadas",
        "description": "Configuração de regras de passadas por prova e categoria (limites, tempos, bois)."
    },
    {
        "name": "Controle Participação",
        "description": "Controle individual de quantas vezes cada competidor pode participar por prova/categoria."
    },
    {
        "name": "Rankings Passadas",
        "description": "Rankings específicos por passada, tempo e pontuação de cada corrida."
    },
    {
        "name": "Relatórios Passadas",
        "description": "Relatórios detalhados de performance por passada e resumos de trios."
    },
    {
        "name": "Estatísticas Passadas",
        "description": "Estatísticas avançadas de tempos, distribuição e performance das passadas."
    },
    {
        "name": "Dashboard Passadas",
        "description": "Dashboard em tempo real com monitoramento de passadas do dia."
    },
    {
        "name": "Trio Passadas",
        "description": "Operações específicas de passadas para trios individuais."
    },
    {
        "name": "Exportação Passadas",
        "description": "Exportação de dados de passadas em formatos estruturados."
    },
    
    # Resultados
    {
        "name": "Resultado",
        "description": "Gerencia resultados de trios nas provas (tempos, colocações, premiações)."
    },
    {
        "name": "Resultado Consulta",
        "description": "Consultas de resultados por prova, trio e categoria."
    },
    {
        "name": "Resultado Ranking",
        "description": "Rankings detalhados baseados em resultados."
    },
    {
        "name": "Resultado Lote",
        "description": "Lançamento de resultados em lote e cálculos automáticos."
    },
    {
        "name": "Resultado Pontuação",
        "description": "Cálculo automático de pontuação CONTEP baseado em resultados."
    },
    {
        "name": "Resultado Estatísticas",
        "description": "Estatísticas de performance e tempos por categoria."
    },
    {
        "name": "Resultado Relatórios",
        "description": "Relatórios de performance e análises comparativas."
    },
    {
        "name": "Resultado Exportação",
        "description": "Exportação de resultados em formatos estruturados."
    },
    {
        "name": "Resultado Importação",
        "description": "Importação de resultados via CSV e outros formatos."
    },
    {
        "name": "Resultado Utilitários",
        "description": "Utilitários para correção e recálculo de dados."
    },
    {
        "name": "Resultado Validação",
        "description": "Validação de consistência dos dados de resultados."
    },
    {
        "name": "Resultado Análise",
        "description": "Análises avançadas de distribuição de tempos e performance."
    },
    {
        "name": "Resultado Especial",
        "description": "Processamento completo de provas (resultados + colocações + pontuação)."
    },
    
    # Pontuação
    {
        "name": "Pontuação",
        "description": "Sistema de pontuação CONTEP e por premiação. Gerencia pontos de competidores."
    },
    {
        "name": "Pontuação Consulta",
        "description": "Consultas de pontuação por competidor, prova e categoria."
    },
    {
        "name": "Pontuação Cálculo",
        "description": "Cálculos automáticos de pontuação baseados em resultados."
    },
    {
        "name": "Pontuação Ranking",
        "description": "Rankings de competidores baseados na pontuação CONTEP."
    },
    {
        "name": "Pontuação Estatísticas",
        "description": "Estatísticas detalhadas de pontuação por competidor e categoria."
    },
    {
        "name": "Pontuação Relatórios",
        "description": "Relatórios anuais de pontuação e distribuição de pontos."
    },
    {
        "name": "Pontuação Exportação",
        "description": "Exportação de dados de pontuação em diferentes formatos."
    },
    {
        "name": "Pontuação Importação",
        "description": "Importação de pontuações em lote."
    },
    {
        "name": "Pontuação Validação",
        "description": "Validação de consistência dos cálculos de pontuação."
    },
    {
        "name": "Usuário",
        "description": "Gerenciamento de usuários do sistema."
    },
    # NOVA TAG ADICIONADA PARA O DASHBOARD
    {
        "name": "Dashboard (BI)",
        "description": "Endpoints de dados agregados para alimentar painéis de Business Intelligence (BI)."
    }
]

# ===================================================================
# CONFIGURAÇÃO DO CICLO DE VIDA DA APLICAÇÃO
# ===================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento do ciclo de vida da aplicação"""
    # Startup
    logger.info("🚀 Iniciando Sistema LCTP (Liga de Competição de Team Penning)...")
    
    # Criar tabelas se não existirem
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Estrutura do banco de dados verificada/criada")
    except Exception as e:
        logger.error(f"❌ Erro ao configurar banco de dados: {e}")
        raise
    
    logger.info("🎯 Sistema LCTP iniciado com sucesso!")
    logger.info("📚 Documentação disponível em: /docs")
    logger.info("🔄 Documentação alternativa em: /redoc")
    logger.info("🆕 Novo módulo de Passadas disponível!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Encerrando Sistema LCTP...")

# ===================================================================
# CRIAÇÃO DA APLICAÇÃO FASTAPI
# ===================================================================

app = FastAPI(
    title="Sistema LCTP - Liga de Competição de Team Penning",
    description="""
    ## 🏇 Sistema Completo para Gerenciamento de Competições de Team penning
    
    Sistema desenvolvido seguindo as regras da **LCTP (CONTEP)** para gerenciar 
    competições de team penning de forma completa e profissional.
    
    ### 🏁 **Padrão LCTP/CONTEP:**
    Sistema totalmente aderente ao regulamento oficial da Liga de Competição 
    de Team Penning, agora com controle avançado de múltiplas participações.
    
    ---
    
    **Desenvolvido com ❤️ para a comunidade do Team penning brasileiro**
    
    **Versão 2.0 - Agora com Sistema de Passadas Múltiplas! 🆕**
    """,
    version="2.0.0",
    contact={
        "name": "Sistema LCTP",
        "url": "https://lctp.com.br",
        "email": "suporte@lctp.com.br",
    },
    license_info={
        "name": "Licença LCTP",
        "url": "https://lctp.com.br/licenca",
    },
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# ===================================================================
# CONFIGURAÇÃO DE MIDDLEWARE
# ===================================================================

# CORS - Configurar adequadamente em produção
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção: especificar domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================================================================
# ROTAS PRINCIPAIS DO SISTEMA
# ===================================================================

@app.get("/", tags=["Sistema"], summary="Informações do Sistema")
async def root():
    """
    Retorna informações básicas do Sistema LCTP
    """
    return {
        "sistema": "LCTP - Liga de Competição de Team Penning",
        "versao": "2.0.0",
        "status": "ativo",
        "descricao": "Sistema completo para gerenciamento de competições de team penning",
        "documentacao": "/docs",
        "novidades_v2": [
            "🆕 Sistema de Controle de Passadas",
            "🔄 Múltiplas corridas por trio",
            "⏱️ Controle de limites por competidor",
            "🐂 Gestão de bois por passada",
            "📊 Rankings específicos por passada",
            "📈 Dashboard de monitoramento em tempo real"
        ],
        "funcionalidades": [
            "Gestão de Competidores",
            "Sistema de Trios",
            "Categorias com Regras",
            "Controle de Passadas Múltiplas",
            "Pontuação CONTEP",
            "Rankings e Estatísticas",
            "Relatórios Avançados"
        ],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health", tags=["Sistema"], summary="Verificação de Saúde")
async def health_check():
    """
    Endpoint para verificação de saúde do sistema
    """
    try:
        # Testar conexão com banco
        db = next(get_db())
        db.execute("SELECT 1")
        
        # Verificar tabelas principais
        tabelas_principais = [
            "competidores", "trios", "categorias", "provas", 
            "resultados", "pontuacao", "passadas_trio"  # NOVA TABELA
        ]
        
        db_status = "conectado"
    except Exception as e:
        db_status = f"erro: {str(e)}"
    
    return {
        "status": "ok" if db_status == "conectado" else "erro",
        "timestamp": datetime.now().isoformat(),
        "banco_dados": db_status,
        "versao_sistema": "2.0.0",
        "modulo_passadas": "ativo",
        "novas_funcionalidades": {
            "controle_passadas": True,
            "multiplas_corridas": True,
            "limite_competidores": True,
            "gestao_bois": True
        }
    }

@app.get("/info", tags=["Sistema"], summary="Informações Técnicas")
async def system_info():
    """
    Retorna informações técnicas detalhadas do sistema
    """
    return {
        "sistema": {
            "nome": "Sistema LCTP",
            "versao": "2.0.0",
            "python_version": "3.13+",
            "framework": "FastAPI",
            "novidades_v2": "Sistema de Controle de Passadas"
        },
        "modulos": {
            "competidores": "Gestão completa de competidores",
            "trios": "Formação e sorteios de trios",
            "categorias": "Regras por categoria (Baby, Kids, Mirim, etc.)",
            "provas": "Gerenciamento de eventos e competições",
            "resultados": "Lançamento de tempos e colocações",
            "pontuacao": "Sistema CONTEP de pontuação",
            "passadas": "🆕 Controle de múltiplas corridas por trio"
        },
        "endpoints_disponiveis": {
            "competidores": 20,
            "trios": 15,
            "categorias": 12,
            "provas": 18,
            "resultados": 16,
            "pontuacao": 14,
            "passadas": 22  # NOVOS ENDPOINTS
        },
        "recursos": {
            "sorteios_automaticos": True,
            "validacao_regras": True,
            "calculo_pontuacao": True,
            "rankings_tempo_real": True,
            "relatorios_avancados": True,
            "import_export": True,
            "controle_passadas_multiplas": True,  # NOVO
            "limite_corridas_competidor": True,   # NOVO
            "gestao_bois_passadas": True,         # NOVO
            "dashboard_tempo_real": True          # NOVO
        },
        "sistema_passadas": {
            "max_passadas_configuravel": True,
            "controle_individual_competidor": True,
            "intervalo_entre_passadas": True,
            "gestao_bois_automatica": True,
            "pontuacao_por_passada": True,
            "rankings_especificos": True,
            "validacoes_automaticas": True
        }
    }


# ===================================================================
# INCLUSÃO DAS ROTAS DOS MÓDULOS LCTP
# ===================================================================

# Rotas de Competidores
app.include_router(
    route_competidor.router,
    prefix="/api/v1",
    tags=["Competidores LCTP"]
)

# Rotas de Trios
app.include_router(
    route_trio.router,
    prefix="/api/v1",
    tags=["Trios LCTP"]
)

# Rotas de Categorias
app.include_router(
    route_categoria.router,
    prefix="/api/v1",
    tags=["Categorias LCTP"]
)

# Rotas de Provas
app.include_router(
    route_prova.router,
    prefix="/api/v1",
    tags=["Provas LCTP"]
)

# Rotas de Resultados
app.include_router(
    route_resultado.router,
    prefix="/api/v1",
    tags=["Resultados LCTP"]
)

# Rotas de Pontuação
app.include_router(
    route_pontuacao.router,
    prefix="/api/v1",
    tags=["Pontuação LCTP"]
)

# 🆕 NOVA ROTA: Sistema de Passadas
app.include_router(
    route_passadas.router,
    prefix="/api/v1",
    tags=["Passadas LCTP"]
)

# Rotas de Autenticação
app.include_router(
    route_auth.router,
    prefix="/api/v1",
    tags=["Autenticação"]
)

# Rotas de Usuários
app.include_router(
    route_usuario.router,
    prefix="/api/v1",
    tags=["Usuário"]
)

# ROTA DO DASHBOARD ATUALIZADA
app.include_router(
    route_dashboard.router,
    prefix="/api/v1",
    tags=["Dashboard (BI)"]
)

# ===================================================================
# CONFIGURAÇÃO DE EXCEÇÕES GLOBAIS
# ===================================================================

@app.exception_handler(LCTPException)
async def lctp_exception_handler(request, exc):
    """Handler para exceções específicas do LCTP"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc)
    )

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handler para erros de valor"""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(exc)
    )

# ===================================================================
# INICIALIZAÇÃO DO SERVIDOR
# ===================================================================

if __name__ == "__main__":
    print("🏇 Sistema LCTP v2.0 - Agora com Controle de Passadas! 🆕")
    print("📚 Documentação: http://localhost:8000/docs")
    print("🎯 Novidades: http://localhost:8000/novidades")
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )