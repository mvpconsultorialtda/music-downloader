# -*- coding: utf-8 -*-
"""Varredura: reconstruir o catalogo a partir do disco e do `history.json`.

Duas fontes, com confianca diferente:

- **o nome do arquivo**, quando traz `_[<id>]` -- essa e a convencao nova, e o
  id vem de graca;
- **o `history.json` antigo**, que tem 219 entradas com id e 144 sem nenhum.
  As com id entram no catalogo. As sem id entram em `sem_id`, marcadas
  `incerto`: elas nunca vao ter id, porque o nome do arquivo daquela epoca
  nunca gravou o id. Nao travam download nenhum -- travar por titulo foi
  exatamente o defeito que deixou o mesmo video descer duas vezes.

Nada aqui apaga, move ou renomeia arquivo. Apagar midia e decisao do operador.
"""
import glob
import json
import os
import re

from . import ids as _ids

EXTENSOES = ('.mp3', '.m4a', '.opus', '.webm', '.mp4', '.mkv', '.wav', '.flac')

# `Titulo - 09-11-2025.mp3` e `2026-09-15_Titulo_[id].mp3`: tira a data dos dois.
_DATA_NO_FIM = re.compile(r'\s*-\s*\d{2}-\d{2}-\d{4}$')
_DATA_NO_INICIO = re.compile(r'^\d{4}-\d{2}-\d{2}_')
_CORTE = re.compile(r'_part\d+$')


def assinatura(texto):
    """So letras e digitos, minusculos. Usada para casar titulo com nome de arquivo.

    Nao serve de chave -- serve de palpite, e so para recuperar o id de material
    antigo. A chave e o id.
    """
    return re.sub(r'[^a-z0-9]', '', (texto or '').lower())


def titulo_provavel(nome_do_arquivo):
    """Do nome do arquivo de volta ao titulo, na medida do possivel."""
    base = os.path.splitext(os.path.basename(nome_do_arquivo))[0]
    base = _CORTE.sub('', base)
    base = re.sub(r'_\[' + _ids.ID + r'\]$', '', base)
    base = _DATA_NO_INICIO.sub('', base)
    base = _DATA_NO_FIM.sub('', base)
    return base


def arquivos_de_midia(raiz='output'):
    for caminho in glob.glob(os.path.join(raiz, '**', '*'), recursive=True):
        if os.path.isfile(caminho) and caminho.lower().endswith(EXTENSOES):
            yield caminho


def acervo_do_caminho(caminho, raiz='output'):
    """A pasta imediatamente sob `output/`. Arquivo solto na raiz vira `(raiz)`."""
    relativo = os.path.relpath(caminho, raiz)
    partes = relativo.replace('\\', '/').split('/')
    return partes[0] if len(partes) > 1 else '(raiz)'


def indexar(catalogo, raiz='output', history='history.json'):
    """Reconstroi o catalogo. Devolve o relatorio do que achou.

    Idempotente: rodar de novo nao duplica nada, porque tudo entra por id.
    """
    relatorio = {
        'arquivos_vistos': 0,
        'por_id_no_nome': 0,
        'por_history': 0,
        'sem_id': 0,
        'history_com_id': 0,
        'history_sem_id': 0,
    }

    # --- 1. o history antigo, que e onde estao os ids do material de 2025 ----
    por_assinatura = {}
    if os.path.exists(history):
        with open(history, 'r', encoding='utf-8') as f:
            entradas = json.load(f).get('downloaded', [])
        for entrada in entradas:
            video_id = entrada.get('id')
            if video_id:
                relatorio['history_com_id'] += 1
                catalogo.anotar(video_id, titulo=entrada.get('titulo') or entrada.get('title'),
                                origem='history')
                for chave in (entrada.get('title'), entrada.get('filename')):
                    assinada = assinatura(titulo_provavel(chave or ''))
                    if assinada:
                        por_assinatura.setdefault(assinada, video_id)
            else:
                relatorio['history_sem_id'] += 1

    # --- 2. o disco ---------------------------------------------------------
    for caminho in arquivos_de_midia(raiz):
        relatorio['arquivos_vistos'] += 1
        nome = os.path.basename(caminho)
        acervo = acervo_do_caminho(caminho, raiz)
        formato = 'audio' if caminho.lower().endswith(('.mp3', '.m4a', '.opus', '.wav', '.flac')) else 'video'

        video_id = _ids.do_nome_de_arquivo(nome)
        if video_id:
            relatorio['por_id_no_nome'] += 1
            catalogo.anotar(video_id, acervo=acervo, arquivo=caminho,
                            formato=formato, origem='disco')
            continue

        palpite = por_assinatura.get(assinatura(titulo_provavel(nome)))
        if palpite:
            relatorio['por_history'] += 1
            catalogo.anotar(palpite, acervo=acervo, arquivo=caminho,
                            formato=formato, origem='disco')
            continue

        relatorio['sem_id'] += 1
        catalogo.anotar_sem_id(titulo_provavel(nome), caminho)

    catalogo.gravar()
    return relatorio
