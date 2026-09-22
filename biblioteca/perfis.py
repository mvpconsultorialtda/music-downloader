# -*- coding: utf-8 -*-
"""Perfis: a instrucao de download, escrita e versionada.

Antes havia UMA configuracao global (`config.json`) com um `output_dir` so,
trocado a mao a cada rodada, e uma pilha de `.txt` em `input/`. E por isso que
o `output/` tem cinco pastas do mesmo canal: elas nao sao categorias, sao as
batidas em que alguem rodou o script, congeladas em nome de pasta.

Um perfil junta as duas metades -- para onde vai e o que buscar -- num arquivo
so, nomeado pelo **acervo**. Rodar duas vezes o mesmo perfil cai na mesma
pasta, e o catalogo impede o download repetido.
"""
import json
import os

PASTA_PADRAO = 'perfis'

# O que um perfil pode dizer. Campo fora desta lista e erro de digitacao, e
# erro de digitacao silencioso em filtro de download custa horas de banda.
CAMPOS = {
    'acervo', 'descricao', 'canais_permitidos', 'formato', 'publicado_entre',
    'duracao_minima_minutos', 'duracao_maxima_minutos', 'corte', 'alvos',
    'resultados_por_busca',
}

CORTE_CAMPOS = {'ativo', 'limiar_minutos', 'max_minutos', 'min_minutos'}


class PerfilInvalido(Exception):
    pass


def caminho(nome, pasta=PASTA_PADRAO):
    if nome.endswith('.json'):
        return os.path.join(pasta, nome) if not os.path.isabs(nome) else nome
    return os.path.join(pasta, f'{nome}.json')


def listar(pasta=PASTA_PADRAO):
    if not os.path.isdir(pasta):
        return []
    return sorted(os.path.splitext(f)[0] for f in os.listdir(pasta) if f.endswith('.json'))


def carregar(nome, pasta=PASTA_PADRAO):
    """Le o perfil e valida. Devolve o dicionario com os padroes preenchidos."""
    caminho_arquivo = caminho(nome, pasta)
    if not os.path.exists(caminho_arquivo):
        disponiveis = ', '.join(listar(pasta)) or '(nenhum)'
        raise PerfilInvalido(
            f'perfil "{nome}" nao existe em {pasta}/. Disponiveis: {disponiveis}')
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        perfil = json.load(f)
    return validar(perfil, origem=caminho_arquivo)


def validar(perfil, origem='(em memoria)'):
    if not isinstance(perfil, dict):
        raise PerfilInvalido(f'{origem}: o perfil precisa ser um objeto JSON')

    desconhecidos = set(perfil) - CAMPOS
    if desconhecidos:
        raise PerfilInvalido(
            f'{origem}: campo desconhecido {sorted(desconhecidos)}. '
            f'Campos aceitos: {sorted(CAMPOS)}')

    acervo = perfil.get('acervo')
    if not acervo or not isinstance(acervo, str):
        raise PerfilInvalido(f'{origem}: "acervo" e obrigatorio -- e o nome da pasta de saida')
    if os.sep in acervo or '/' in acervo or acervo in ('.', '..'):
        raise PerfilInvalido(f'{origem}: "acervo" e um nome de pasta simples, sem barra')

    formato = perfil.setdefault('formato', 'audio')
    if formato not in ('audio', 'video'):
        raise PerfilInvalido(f'{origem}: "formato" e "audio" ou "video", nao {formato!r}')

    alvos = perfil.setdefault('alvos', [])
    if not isinstance(alvos, list) or any(not isinstance(a, str) for a in alvos):
        raise PerfilInvalido(f'{origem}: "alvos" e uma lista de URLs ou termos de busca')

    canais = perfil.setdefault('canais_permitidos', [])
    if not isinstance(canais, list):
        raise PerfilInvalido(f'{origem}: "canais_permitidos" e uma lista')

    janela = perfil.get('publicado_entre')
    if janela is not None:
        if not isinstance(janela, list) or len(janela) != 2:
            raise PerfilInvalido(f'{origem}: "publicado_entre" e ["AAAA-MM-DD", "AAAA-MM-DD"]')

    corte = perfil.setdefault('corte', {'ativo': False})
    if not isinstance(corte, dict) or (set(corte) - CORTE_CAMPOS):
        raise PerfilInvalido(
            f'{origem}: "corte" aceita apenas {sorted(CORTE_CAMPOS)}')
    corte.setdefault('ativo', False)
    corte.setdefault('limiar_minutos', 20)
    corte.setdefault('max_minutos', 15)
    corte.setdefault('min_minutos', 5)

    perfil.setdefault('resultados_por_busca', 10)
    return perfil
