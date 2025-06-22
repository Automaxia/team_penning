from passlib.context import CryptContext

#pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
pwd_context = CryptContext(schemes=["bcrypt"])

async def verifica_hash(texto_plano, texto_hashed) -> bool:
    return pwd_context.verify(texto_plano, texto_hashed)

async def gerar_hash(texto_plano):
    return pwd_context.hash(texto_plano)