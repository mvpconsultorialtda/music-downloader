# -*- coding: utf-8 -*-
"""Levar o acervo antigo para a convencao nova -- movendo, nunca apagando.

Duas coisas separadas, e so a primeira e segura de rodar sozinha:

1. **renomear**: `Titulo - 09-11-2025.mp3` vira
   `2025-11-09_Titulo_[<id>].mp3`. O id vem do catalogo. Depois disso o
   arquivo se explica sozinho e a varredura nao depende mais de adivinhar
   titulo. Reversivel: o catalogo guarda o caminho antigo e o novo.

2. **juntar**: `raul_sena`, `raul_sena_2`, `raul_sena_2025_mar`,
   `raul_sena_2025_new` e `raul_sena_batch5` nao sao cinco categorias -- sao
   cinco batidas do mesmo acervo. Juntar move os arquivos para uma pasta so.

O que NAO esta aqui, de proposito: apagar. Quando dois arquivos disputam o
mesmo destino, o segundo e deixado onde esta e entra no relatorio de conflito.
Qual versao fica e decisao do operador (duvida 4).
"""
import os
import re
import shutil

from . import ids as _ids, varredura

_DATA_NO_FIM = re.compile(r'\s*-\s*(\d{2})-(\d{2})-(\d{4})$')


def nome_novo(caminho, video_id, publicado=None):
    """O nome deste arquivo na convencao nova, ou None se ja estiver nela."""
    base, extensao = os.path.splitext(os.path.basename(caminho))
    if _ids.do_nome_de_arquivo(base):
        return None  # ja tem id no nome

    corte = ''
    achado = re.search(r'(_part\d+)$', base)
    if achado:
        corte = achado.group(1)
        base = base[:achado.start()]

    data = publicado
    achado = _DATA_NO_FIM.search(base)
    if achado:
        base = base[:achado.start()]
        data = data or f'{achado.group(3)}-{achado.group(2)}-{achado.group(1)}'

    titulo = re.sub(r'[^0-9A-Za-z_-]+', '_', base).strip('_') or 'sem_titulo'
    prefixo = f'{data}_' if data else ''
    return f'{prefixo}{titulo}{corte}_[{video_id}]{extensao}'


def planejar(catalogo, raiz='output', de=None, para=None):
    """Monta a lista de movimentos. Nao toca em disco nenhum.

    `de` e a lista de pastas a juntar (relativas a `raiz`); `para` e o acervo
    de destino. Sem os dois, so renomeia cada arquivo onde ele ja esta.
    """
    de = [d.strip('/\\') for d in (de or [])]
    movimentos, conflitos, sem_id = [], [], []
    destinos = set()

    # O caminho de cada arquivo de volta ao seu id, pelo catalogo.
    dono = {}
    for video_id, reg in catalogo.itens.items():
        for arquivo in reg.get('arquivos', []):
            dono[os.path.normcase(os.path.normpath(arquivo))] = (video_id, reg)

    for caminho in varredura.arquivos_de_midia(raiz):
        acervo = varredura.acervo_do_caminho(caminho, raiz)
        if de and acervo not in de:
            continue

        chave = os.path.normcase(os.path.normpath(caminho))
        achado = dono.get(chave)
        if not achado:
            sem_id.append(caminho)
            continue
        video_id, reg = achado

        acervo_destino = para or acervo
        novo = nome_novo(caminho, video_id, reg.get('publicado'))
        if novo is None and acervo_destino == acervo:
            continue  # ja esta no lugar e no formato certos

        pasta_destino = raiz if acervo_destino == '(raiz)' else os.path.join(raiz, acervo_destino)
        destino = os.path.join(pasta_destino, novo or os.path.basename(caminho))

        if os.path.normcase(os.path.normpath(destino)) == chave:
            continue

        if os.path.exists(destino) or os.path.normcase(os.path.normpath(destino)) in destinos:
            conflitos.append({'de': caminho, 'para': destino, 'id': video_id})
            continue

        destinos.add(os.path.normcase(os.path.normpath(destino)))
        movimentos.append({'de': caminho, 'para': destino, 'id': video_id})

    return {'movimentos': movimentos, 'conflitos': conflitos, 'sem_id': sem_id}


def aplicar(plano, catalogo, raiz='output'):
    """Executa os movimentos e corrige os caminhos no catalogo.

    Move -- `shutil.move` -- e nunca sobrescreve: o plano ja separou os
    conflitos. Se um movimento falhar, os anteriores ficam e o catalogo e
    gravado assim mesmo, porque o disco ja mudou.
    """
    feitos, falhas = [], []
    try:
        for movimento in plano['movimentos']:
            try:
                os.makedirs(os.path.dirname(movimento['para']), exist_ok=True)
                shutil.move(movimento['de'], movimento['para'])
                _trocar_caminho(catalogo, movimento, raiz)
                feitos.append(movimento)
            except Exception as e:
                falhas.append(dict(movimento, erro=str(e)))
    finally:
        catalogo.gravar()
    return {'feitos': feitos, 'falhas': falhas}


def _trocar_caminho(catalogo, movimento, raiz):
    reg = catalogo.registro(movimento['id'])
    if not reg:
        return
    antigo = os.path.normcase(os.path.normpath(movimento['de']))
    try:
        novo = os.path.relpath(movimento['para'], os.getcwd())
    except ValueError:
        novo = movimento['para']  # outro drive no Windows
    novo = novo.replace('\\', '/')
    reg['arquivos'] = [
        novo if os.path.normcase(os.path.normpath(a)) == antigo else a
        for a in reg.get('arquivos', [])
    ]
    if novo not in reg['arquivos']:
        reg['arquivos'].append(novo)
    reg['acervo'] = varredura.acervo_do_caminho(movimento['para'], raiz)
