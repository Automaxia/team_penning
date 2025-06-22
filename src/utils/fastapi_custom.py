from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRouter
from typing import Callable, Any

from src.database.models import ApiResponse

class CustomAPIRouter(APIRouter):
    """
    Router personalizado que processa as respostas para garantir o formato padronizado
    e definir o código de status HTTP correto.
    """
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> Response:
            response = await original_route_handler(request)
            
            # Se a resposta já for um Response do FastAPI, retorna como está
            if isinstance(response, Response):
                return response
                
            # Se a resposta for um ApiResponse personalizado, extrai o código de status
            # e retorna o objeto JSON com o status_code apropriado
            if isinstance(response, ApiResponse):
                status_code = response.status_code
                # Remove o status_code do objeto antes de serializar para JSON
                response_dict = response.dict()
                del response_dict["status_code"]
                
                # Cria uma nova resposta JSON com o status_code correto
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    content=response_dict,
                    status_code=status_code
                )
                
            return response
            
        return custom_route_handler


# Exemplo de configuração no aplicativo principal
def configure_app(app: FastAPI):
    """
    Configura o aplicativo FastAPI para usar o router personalizado por padrão.
    """
    # Define o router personalizado como padrão
    app.router_class = CustomAPIRouter
    
    # Configura outras opções do aplicativo, se necessário
    return app