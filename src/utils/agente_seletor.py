from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from src.repositorios.telefone import RepositorioTelefone
import logging

class AgenteSeletor:
    @staticmethod
    async def selecionar_agente(db: Session, sq_telefone: int, dados_webhook: Dict[str, Any] = None) -> Optional[int]:
        """
        Seleciona o agente mais apropriado para um telefone específico baseado no contexto.
        
        Args:
            db: Sessão do banco de dados
            sq_telefone: ID do telefone
            dados_webhook: Dados do webhook do WhatsApp
            
        Returns:
            ID do agente selecionado ou None se nenhum for encontrado
        """
        try:
            # Extrair informações relevantes do webhook
            contexto = {}
            
            if dados_webhook:
                # Extrair mensagem
                if 'message' in dados_webhook:
                    contexto['mensagem'] = dados_webhook['message']
                
                # Extrair tipo de mídia
                if 'message_type' in dados_webhook:
                    contexto['tipo_midia'] = dados_webhook['message_type']
                
                # Verificar se é cliente novo (mensagens anteriores = 0)
                if 'session' in dados_webhook and 'mensagens_anteriores' in dados_webhook['session']:
                    contexto['cliente_novo'] = dados_webhook['session']['mensagens_anteriores'] == 0
            
            # Adicionar hora atual
            contexto['hora'] = datetime.now().time()
            
            # Usar repositório para selecionar agente
            repo = RepositorioTelefone(db)
            sq_agente = await repo.selecionar_agente_para_telefone(sq_telefone, contexto)
            
            return sq_agente
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao selecionar agente: {str(e)}")
            return None