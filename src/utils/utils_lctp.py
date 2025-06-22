from datetime import date, datetime
from typing import List, Dict, Any, Optional
import random

class UtilsLCTP:
    """Utilitários para o sistema LCTP"""
    
    @staticmethod
    def calcular_idade(data_nascimento: date) -> int:
        """Calcula idade atual baseada na data de nascimento"""
        hoje = date.today()
        idade = hoje.year - data_nascimento.year
        if (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day):
            idade -= 1
        return idade
    
    @staticmethod
    def calcular_pontos_colocacao(colocacao: int) -> float:
        """Calcula pontos baseado na colocação (tabela CONTEP)"""
        return ConfigLCTP.PONTUACAO_CONTEP.get(colocacao, 0)
    
    @staticmethod
    def calcular_pontos_premiacao(valor_premiacao: float) -> float:
        """Calcula pontos baseado na premiação (R$100 = 1 ponto)"""
        if not valor_premiacao:
            return 0
        return valor_premiacao / ConfigLCTP.VALOR_BASE_PONTUACAO
    
    @staticmethod
    def calcular_premiacao_liquida(valor_bruto: float, percentual_desconto: float = None) -> float:
        """Calcula premiação líquida após desconto"""
        if not valor_bruto:
            return 0
        
        desconto = percentual_desconto or ConfigLCTP.DESCONTO_PREMIACAO_PADRAO
        return valor_bruto * (1 - desconto / 100)
    
    @staticmethod
    def validar_handicap(handicap: int) -> bool:
        """Valida se o handicap está dentro dos limites"""
        return ConfigLCTP.MIN_HANDICAP <= handicap <= ConfigLCTP.MAX_HANDICAP
    
    @staticmethod
    def determinar_categoria_idade(idade: int) -> List[str]:
        """Determina categorias possíveis baseado na idade"""
        categorias = ['aberta']  # Sempre pode participar da aberta
        
        if idade <= 12:
            categorias.append('baby')
        elif 13 <= idade <= 17:
            categorias.append('kids')
        
        # Mirim tem restrição de soma de idades, não individual
        categorias.append('mirim')
        
        return categorias
    
    @staticmethod
    def embaralhar_lista(lista: List[Any]) -> List[Any]:
        """Embaralha uma lista de forma segura"""
        lista_copia = lista.copy()
        random.shuffle(lista_copia)
        return lista_copia
    
    @staticmethod
    def formar_grupos_tres(lista: List[Any]) -> List[List[Any]]:
        """Forma grupos de 3 elementos de uma lista"""
        grupos = []
        for i in range(0, len(lista) - 2, 3):
            grupos.append(lista[i:i+3])
        return grupos
    
    @staticmethod
    def validar_cpf(cpf: str) -> bool:
        """Valida CPF (implementação básica)"""
        # Remove caracteres não numéricos
        cpf = ''.join(filter(str.isdigit, cpf))
        
        # Verifica se tem 11 dígitos
        if len(cpf) != 11:
            return False
        
        # Verifica sequências inválidas
        if cpf == cpf[0] * 11:
            return False
        
        # Cálculo dos dígitos verificadores
        def calcular_digito(cpf_parcial):
            soma = sum(int(cpf_parcial[i]) * (len(cpf_parcial) + 1 - i) for i in range(len(cpf_parcial)))
            resto = soma % 11
            return 0 if resto < 2 else 11 - resto
        
        # Verifica primeiro dígito
        if int(cpf[9]) != calcular_digito(cpf[:9]):
            return False
        
        # Verifica segundo dígito
        if int(cpf[10]) != calcular_digito(cpf[:10]):
            return False
        
        return True