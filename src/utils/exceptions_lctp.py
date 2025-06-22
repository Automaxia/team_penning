class LCTPException(Exception):
    """Exceção base para o sistema LCTP"""
    pass

class CompetidorException(LCTPException):
    """Exceções relacionadas a competidores"""
    pass

class TrioException(LCTPException):
    """Exceções relacionadas a trios"""
    pass

class CategoriaException(LCTPException):
    """Exceções relacionadas a categorias"""
    pass

class SorteioException(LCTPException):
    """Exceções relacionadas a sorteios"""
    pass

class PontuacaoException(LCTPException):
    """Exceções relacionadas a pontuação"""
    pass

class HandicapInvalidoException(CompetidorException):
    """Handicap fora dos limites permitidos"""
    def __init__(self, handicap: int):
        super().__init__(f"Handicap {handicap} inválido. Deve estar entre {ConfigLCTP.MIN_HANDICAP} e {ConfigLCTP.MAX_HANDICAP}")

class TrioInvalidoException(TrioException):
    """Trio não atende às regras da categoria"""
    def __init__(self, motivo: str):
        super().__init__(f"Trio inválido: {motivo}")

class SorteioInvalidoException(SorteioException):
    """Sorteio não pode ser realizado"""
    def __init__(self, motivo: str):
        super().__init__(f"Sorteio inválido: {motivo}")