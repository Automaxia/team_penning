import random
from collections import defaultdict

def gerar_trios(nomes, total_participacoes, tamanho_trio=3, max_iter=5000):
    if len(nomes) < tamanho_trio:
        print("Poucos nomes para formar um trio.")
        return [], {}

    participacao = defaultdict(int)
    trios_selecionados = []
    max_trios = (len(nomes) * total_participacoes) // tamanho_trio

    # Cria uma fila dos nomes para distribuir participações de forma justa
    nomes_fila = list(nomes)
    random.shuffle(nomes_fila)
    rodada = 0
    iteracoes = 0

    while True:
        iteracoes += 1
        if iteracoes > max_iter:
            print(f"\nLimite de {max_iter} iterações atingido! Interrompendo para evitar loop infinito.")
            break

        # Filtra só quem pode participar mais (não chegou ao limite)
        elegiveis = [n for n in nomes_fila if participacao[n] < total_participacoes]
        if len(elegiveis) < tamanho_trio:
            break  # Não fecha mais um trio

        # Ordena os elegíveis por quem menos jogou (prioriza quem participou menos)
        elegiveis.sort(key=lambda n: participacao[n])

        # Seleciona trio (priorizando quem participou menos)
        trio = tuple(elegiveis[:tamanho_trio])
        trios_selecionados.append(trio)
        for n in trio:
            participacao[n] += 1

        rodada += 1
        if rodada > max_trios * 2:
            # Limite máximo de rodadas para evitar travamento lógico (segurança extra)
            print(f"\nLimite interno de rodadas atingido! Interrompendo para evitar loop infinito.")
            break

    # Relatório final
    print("Trios sorteados:")
    for idx, trio in enumerate(trios_selecionados, 1):
        print(f"Trio {idx}: {', '.join(trio)}")

    print("\nResumo de participação:")
    for nome in nomes:
        print(f"{nome}: {participacao[nome]} trios")
    faltantes = [nome for nome in nomes if participacao[nome] < total_participacoes]
    if faltantes:
        print("\nNão foi possível dar todas as participações desejadas. Estes nomes ficaram com menos trios:", faltantes)
    else:
        print("\nTodos participaram do número desejado de trios!")

    return trios_selecionados, participacao

# Exemplo de uso:
nomes = [
    "Allana", "Ana Gabriela", "Luísa", "Clara"
]
TOTAL_PARTICIPACOES = 3

gerar_trios(nomes, TOTAL_PARTICIPACOES)
