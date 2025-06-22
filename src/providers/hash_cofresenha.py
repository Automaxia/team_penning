import traceback
import base64

async def gerar_hash(texto_plano):
    senha = texto_plano.encode("ascii")
    senha = base64.b64encode(senha)
    return senha.decode("ascii")

async def decripta_hash(texto_plano):
    try:
        texto_plano = base64.b64decode(texto_plano)
        senha = texto_plano.decode("ascii")
        return senha
    except Exception as error:
        print('error', traceback.format_exc())