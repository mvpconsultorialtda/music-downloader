# -*- coding: utf-8 -*-
"""Varredura: reconstruir o catalogo a partir do disco e do `history.json`.

Duas fontes, com confianca diferente:

- **o nome do arquivo**, quando traz `_[<id>]` -- essa e a convencao nova, e o
  id vem de graca;
- **o `history.json` antigo** (em `legado/`), que tem 219 entradas com id e 144
  sem nenhum. As com id entram no catalogo.

O que nao consegue id vai para `sem_id`, e ali sao **dois casos diferentes**:
`id-perdido` para quem desceu do baixador e teve o id descartado pelo `outtmpl`
antigo -- isso e perda --, e `nao-e-do-youtube` para sample de musica e arquivo
local, que nunca teve id e nao devia ter. Na biblioteca real sao 15 e 28, nao
43 "incertos"; somar os dois faz a biblioteca parecer pior do que esta.

Nenhum dos dois trava download -- travar por titulo foi exatamente o defeito
que deixou o mesmo video descer duas vezes.

Nada aqui apaga, move ou renomeia arquivo. Apagar midia e decisao do operador.
"""
import glob
import json
import os
import re
import unicodedata

from . import ids as _ids

EXTENSOES = ('.mp3', '.m4a', '.opus', '.webm', '.mp4', '.mkv', '.wav', '.flac')

# `Titulo - 09-11-2025.mp3` e `2026-09-15_Titulo_[id].mp3`: tira a data dos dois.
_DATA_NO_FIM = re.compile(r'\s*-\s*\d{2}-\d{2}-\d{4}$')
_DATA_NO_INICIO = re.compile(r'^\d{4}-\d{2}-\d{2}_')
_CORTE = re.compile(r'_part\d+$')


def assinatura(texto):
    """So letras e digitos, minusculos, com acento DOBRADO e nao jogado fora.

    Usada para casar titulo com nome de arquivo. Nao serve de chave -- serve de
    palpite, e so para recuperar o id de material antigo. A chave e o id.

    O `NFKD` antes do filtro e obrigatorio, e `docs/DOC-TECNICO.md` ja avisava:
    sem ele "está" perde o acento inteiro e vira "est", enquanto o nome do
    arquivo (que o yt-dlp sanitizou para ASCII) tem "esta". O par nao casa, e o
    arquivo fica marcado incerto sem motivo. Com NFKD o "á" vira "a" + acento
    combinante, o filtro descarta so o acento, e os dois lados dao "esta".
    """
    decomposto = unicodedata.normalize('NFKD', texto or '')
    sem_acento = ''.join(c for c in decomposto if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', sem_acento.lower())


def titulo_provavel(nome_do_arquivo):
    """Do nome do arquivo de volta ao titulo, na medida do possivel."""
    base = os.path.splitext(os.path.basename(nome_do_arquivo))[0]
    base = _CORTE.sub('', base)
    base = re.sub(r'_\[' + _ids.ID + r'\]$', '', base)
    base = _DATA_NO_INICIO.sub('', base)
    base = _DATA_NO_FIM.sub('', base)
    return base


def veio_do_baixador(nome_do_arquivo):
    """True se o nome traz a marca do `outtmpl` antigo: termina em ` - DD-MM-AAAA`.

    E o que separa dois casos que nada tem em comum, e que a primeira versao
    somava num balde so chamado "incerto":

    - **id-perdido** -- desceu do YouTube e o id nao foi gravado. Isso e perda,
      e e o que o Defeito 2 custou.
    - **nao-e-do-youtube** -- sample de musica, gravacao local, arquivo que
      alguem largou na pasta. Nunca teve id e nao ter id nao e defeito.

    Somar os dois faz a biblioteca parecer mais avariada do que esta.
    """
    base = os.path.splitext(os.path.basename(nome_do_arquivo))[0]
    return bool(_DATA_NO_FIM.search(_CORTE.sub('', base)))


def arquivos_de_midia(raiz='output'):
    for caminho in glob.glob(os.path.join(raiz, '**', '*'), recursive=True):
        if os.path.isfile(caminho) and caminho.lower().endswith(EXTENSOES):
            yield caminho


def acervo_do_caminho(caminho, raiz='output'):
    """A pasta imediatamente sob `output/`. Arquivo solto na raiz vira `(raiz)`."""
    relativo = os.path.relpath(caminho, raiz)
    partes = relativo.replace('\\', '/').split('/')
    return partes[0] if len(partes) > 1 else '(raiz)'


# O `history.json` e fonte de MIGRACAO, nao fonte da verdade -- a fonte e o
# `catalogo.json`. Por isso ele mora em `legado/`. A raiz continua sendo olhada
# para quem tem uma copia antiga la, ou clonou o repo antes da mudanca.
HISTORY_CANDIDATOS = (os.path.join('legado', 'history.json'), 'history.json')


def achar_history(caminho=None):
    """O `history.json` a usar: o que foi pedido, ou o primeiro que existir."""
    if caminho:
        return caminho
    for candidato in HISTORY_CANDIDATOS:
        if os.path.exists(candidato):
            return candidato
    return HISTORY_CANDIDATOS[0]


def indexar(catalogo, raiz='output', history=None):
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
        'id_perdido': 0,
        'nao_e_do_youtube': 0,
        'reclassificados': 0,
    }

    # --- 1. o history antigo, que e onde estao os ids do material de 2025 ----
    history = achar_history(history)
    relatorio['history'] = history
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

        situacao = 'id-perdido' if veio_do_baixador(nome) else 'nao-e-do-youtube'
        relatorio['id_perdido' if situacao == 'id-perdido' else 'nao_e_do_youtube'] += 1
        relatorio['sem_id'] += 1
        catalogo.anotar_sem_id(titulo_provavel(nome), caminho, situacao=situacao)

    # --- 3. classificar o que ficou de uma versao anterior -------------------
    # `incerto` era o rotulo unico da primeira versao. A classificacao sai do
    # nome do arquivo guardado, entao ela funciona mesmo para midia que nao
    # esta NESTE disco -- e num clone, nenhuma esta.
    for item in catalogo.sem_id:
        if item.get('situacao') in (None, 'incerto'):
            item['situacao'] = ('id-perdido' if veio_do_baixador(item.get('arquivo') or '')
                                else 'nao-e-do-youtube')
            relatorio['reclassificados'] += 1

    catalogo.gravar()
    return relatorio
