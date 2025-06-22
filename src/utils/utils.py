import os
import io
import json, traceback
from datetime import datetime, timezone
import pytz
from src.database import models

AMSP = pytz.timezone('America/Sao_Paulo')

from fastapi import status, HTTPException
from functools import wraps
def ja_existe_registro_cadastrado(func):
    @wraps(func) #pega as propriedades da função declarada como parametro e atribui na função abaixo 
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Já existe um cliente cadastrado com esse nome informado!')
    return inner

def pega_dados_configuracao():
    try:
        dir_json = os.getcwd() + '/config.json'

        with io.open(dir_json, 'r', encoding='utf_8_sig') as f:
            arq_json = json.load(f)

        return arq_json
    except Exception as erro:
        return erro

def monta_dados_colunas(model, colunas, chave, tabela, remove = False):
    json_coluna = {}

    for coluna in colunas:
        json_coluna.update({coluna:model[coluna]})

    if remove:
        json_coluna.pop(chave)
    param = {
        "tabela": tabela,
        "chave": chave,
        "colunas": json_coluna
    }
    return param

def ler_arquivo(arquivo):
    dados = []
    if os.path.isfile(arquivo):
        with open(arquivo, 'r', encoding='utf_8_sig') as f:
            try:
                dados = json.load(f)
            except:
                dados = []
    return dados

def grava_error_arquivo(json_error):
    from datetime import date

    arquivo = "logError_" + str(date.today()).replace('-','')+'.json'
    dir_logs = os.getcwd() + "/logs/"+arquivo
    os.makedirs(os.getcwd() + "/logs", exist_ok=True)

    #print(dir_logs)
    dados_json = ler_arquivo(dir_logs)
    
    conteudo = []
    if dados_json != '':
        dados_json.append(json_error)
        conteudo = dados_json
    else:
        conteudo.append(json_error)

    conteudo = str(conteudo).replace('"', '\\"')
    conteudo = str(conteudo).replace("'", '"')
    conteudo = str(conteudo).replace(': "None"', ': null')
    conteudo = str(conteudo).replace(": None", ': null')
    
    with open(dir_logs, "w", encoding='utf_8_sig') as outfile:
        outfile.write(str(conteudo))

def envio_email(subject, html_corpo, email_user, arquivos = []):
        import pathlib
        from email import encoders
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        import smtplib
        

        try:
            json_config = pega_dados_configuracao()
            fromaddr = json_config['config_email']['fromaddr']
            password = json_config['config_email']['password']
            toaddr = email_user
            host = json_config['config_email']['host']
            port = json_config['config_email']['port']
            msg = MIMEMultipart()
            
            msg['From'] = fromaddr
            msg['To'] = toaddr
            msg['Subject'] = subject
            toaddr = toaddr.split(';')
            body = html_corpo

            msg.attach(MIMEText(body, 'html'))

            #dir_atual = os.getcwd()

            #filename = "Registro_Atividade_" + str(date.today()) + '.csv'
            #arquivolog = [fr'{dir_atual}\logs\{filename}']                        

            #print(arquivolog)
            if len(arquivos) > 0:
                for f in arquivos:
                    attachment = open(f, 'rb')
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload((attachment).read())
                    encoders.encode_base64(part)
                    #part.add_header('Content-Disposition',"attachment; filename= %s" % filename)
                    part.add_header('Content-Disposition','attachment; filename="%s"'% os.path.basename(f))

                    msg.attach(part)
                    attachment.close()

            server = smtplib.SMTP(host, port)
            server.starttls()
            server.login(fromaddr, password)
            text = msg.as_string()
            toaddrs = toaddr
            retorno = server.sendmail(fromaddr, toaddrs, text)
            #print('email: ', fromaddr, toaddrs, text)
            server.quit()
            return retorno
        except Exception as error:
            utc_dt = datetime.now(timezone.utc)
            dataErro = utc_dt.astimezone(AMSP)
            grava_error_arquivo({"error": f"""{traceback.format_exc()}""","data": str(dataErro)})


def response_error(error):
    return models.ErrorResponse(success=False, message=str(error))

def response_success(data, msg='Registro encontrado com sucesso!'):
    if not isinstance(data, list):
        data = [data]  # Ensure data is a list
    else:
        data = [obj.__dict__ for obj in data]
        for item in data:
            item.pop('_sa_instance_state', None)
    return models.SuccessResponse(success=True, data=data, message=msg)
    
def calcular_similaridade(texto1, texto2):
    if not texto1 or not texto2:
        return 0
        
    texto1 = texto1.lower()
    texto2 = texto2.lower()
    
    # Verifica se um texto contém o outro
    if texto1 in texto2 or texto2 in texto1:
        return 0.8
        
    # Verifica palavras em comum
    palavras1 = set(texto1.split())
    palavras2 = set(texto2.split())
    palavras_comuns = palavras1.intersection(palavras2)
    
    if palavras_comuns:
        return len(palavras_comuns) / max(len(palavras1), len(palavras2))
        
    return 0