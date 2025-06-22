from fastapi import APIRouter, HTTPException, status, Query
import socket, requests
import platform, os, pytz
from src.utils import utils
from typing import List, Optional
from datetime import datetime, date, timezone

AMSP = pytz.timezone('America/Sao_Paulo')

router = APIRouter(tags=['Util'])

#@router.get('/dados')
#def listar_dados(usuario: schemas.Usuario = Depends(obter_usuario_logado), db: Session = Depends(get_db)):

@router.get("/ip_local", tags=['Util'], status_code=status.HTTP_200_OK)
async def pega_ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1))  # connect() for UDP doesn't send packets
    ip_address = s.getsockname()[0]

    return {'ip': ip_address, 'hostname': socket.gethostname(), 'os': platform.platform()}

@router.get("/variaveis", tags=['Util'], status_code=status.HTTP_200_OK)
async def pega_variaveis():
    var = os.getenv('AWS_CONTAINER_CREDENTIALS_RELATIVE_URI')

    env_var = os.environ
    envs = []
    #for env in env_var:
    #    envs.append({'env': env, 'valor': env_var[env]})

    utc_dt = datetime.now(timezone.utc)
    dataErro = utc_dt.astimezone(AMSP)

    response = requests.get('http://169.254.169.254/latest/meta-data/iam/security-credentials/MyIAMRole')
    if response.status_code == 200:
        data = response.json()
        os.environ['AWS_ACCESS_KEY_ID'] = data['AccessKeyId']
        os.environ['AWS_SECRET_ACCESS_KEY'] = data['SecretAccessKey']
        os.environ['AWS_SESSION_TOKEN'] = data['Token']
    else:
        raise Exception('Failed to get AWS credentials')
    
    response = requests.get(f"http://169.254.170.2{os.getenv('AWS_CONTAINER_CREDENTIALS_RELATIVE_URI')}")
    if response.status_code == 200:
        data1 = response.json()
        os.environ['AWS_ACCESS_KEY_ID'] = data1['AccessKeyId']
        os.environ['AWS_SECRET_ACCESS_KEY'] = data1['SecretAccessKey']
        os.environ['AWS_SESSION_TOKEN'] = data1['Token']
    else:
        raise Exception('Failed to get AWS credentials')

    return {'var': var, 'now': datetime.now(), 'timezone': datetime.now(timezone.utc), 'timezone2': datetime.now(timezone.utc).astimezone(AMSP), 'dataErro': dataErro, 'data': data, 'data1':data1}

@router.get("/envio-email", tags=['Util'], status_code=status.HTTP_200_OK)
async def carrega_tarefas_por_usuario(subject: Optional[str] = Query(default=None, max_length=200), 
                                        html_corpo: Optional[str] = Query(default=None, max_length=1000),
                                        email_user: Optional[str] = Query(default=None, max_length=100)):

    retorno = utils.envio_email(subject, html_corpo, email_user, [])
    return True
    if not retorno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Não foi encontrado nenhum registro para o n° de CPF informado!')
    return retorno