from datetime import datetime, timedelta, timezone
from jose import jwt
import pytz, traceback, json
from src.utils import utils
from src.utils.error_handler import handle_error
from dotenv import dotenv_values

#CONFIG  automaxia-automation-bot

config = dotenv_values(".env")
config = json.loads((json.dumps(config) ))

AMSP = pytz.timezone('America/Sao_Paulo')

async def gerar_access_token(data: dict, expira_min: int = config['EXPIRES_IN_MIN']) -> str:
    try:
        dados = data.copy()
        utc_dt = datetime.now(timezone.utc)
        dataAtual = utc_dt.astimezone(AMSP)

        if expira_min == '':
            expira_min = int(config['EXPIRES_IN_MIN'])

        expira = dataAtual + timedelta(minutes=int(expira_min))
        expira = str(expira).replace('-03:00', '')

        dados.update({'expira': expira})
        token_jwt = jwt.encode(dados, config['SECRET_KEY'], algorithm=config['ALGORITHM'])
        return token_jwt
    except Exception as error:
        print(traceback.format_exc())

async def verificar_access_token(token: str):
    try:
        # Check if the token has the correct number of segments
        if token.count('.') != 2:
            raise JWTError("Token format is invalid: Not enough segments")

        payload = jwt.decode(token, config['SECRET_KEY'], algorithms=[config['ALGORITHM']])
        utc_dt = datetime.now(timezone.utc)
        dataAtual = utc_dt.astimezone(AMSP)
        dataAtual = str(dataAtual).replace('-03:00', '').split('.')[0]
        
        expira = payload['expira'].split('.')[0]
        expira = datetime.strptime(expira, '%Y-%m-%d %H:%M:%S')
        dataAtual = datetime.strptime(dataAtual, '%Y-%m-%d %H:%M:%S')

        segundoDif = (expira - dataAtual).total_seconds()
        if segundoDif < 0:
            return 'expirou'

        return payload.get('sub')
    except Exception as error:
        print(traceback.format_exc())
        handle_error(error, verificar_access_token)

# Adicione um método para gerar tokens específicos para APIs
async def gerar_api_token(data: str, expira_min: int = config['EXPIRES_IN_MIN']) -> str:
    return await gerar_access_token(data, expira_min)