class ConfigLCTP:
    """Configurações específicas do sistema LCTP"""
    
    # Pontuação CONTEP (1º ao 10º lugar)
    PONTUACAO_CONTEP = {
        1: 10, 2: 9, 3: 8, 4: 7, 5: 6,
        6: 5, 7: 4, 8: 3, 9: 2, 10: 1
    }
    
    # Conversão premiação para pontos (R$100 = 1 ponto)
    VALOR_BASE_PONTUACAO = 100.0
    
    # Percentual de desconto padrão na premiação
    DESCONTO_PREMIACAO_PADRAO = 5.0
    
    # Regras por categoria
    REGRAS_CATEGORIAS = {
        'baby': {
            'sorteio_completo': True,
            'idade_max': 12
        },
        'kids': {
            'sorteio_parcial': True,
            'min_sorteio': 3,
            'max_sorteio': 9,
            'idade_min': 13,
            'idade_max': 17
        },
        'mirim': {
            'idade_max_trio': 36,
            'sorteio_com_restricao': True
        },
        'feminina': {
            'apenas_feminino': True,
            'sorteio_parcial': True,
            'min_sorteio': 3,
            'max_sorteio': 9
        },
        'aberta': {
            'sem_restricoes': True
        },
        'handicap': {
            'handicap_max_trio': 11
        }
    }
    
    # Ordem de escolha Copa dos Campeões
    ORDEM_HANDICAP_COPA = [0, 1, 2, 3, 4, 5, 7]  # Iniciante, 1, 2, 3, 4, 5, 7
    
    # Limites do sistema
    MAX_HANDICAP = 7
    MIN_HANDICAP = 0
    MAX_IDADE = 100
    MIN_IDADE = 0
    COMPETIDORES_POR_TRIO = 3
