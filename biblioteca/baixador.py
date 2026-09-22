# -*- coding: utf-8 -*-
"""O download, com o id como chave e o id dentro do nome do arquivo.

O que mudou em relacao ao `download_music.py`:

1. A trava de repeticao consulta o catalogo por id (`Catalogo.tem`). Nao existe
   mais comparacao de titulo por substring -- ela errava nos dois sentidos.
2. O `outtmpl` grava `_[<id>]` no fim do nome. Sem isso a varredura de disco
   nunca consegue recuperar o id, e foi assim que 144 entradas cegas nasceram.
3. A saida vai para `output/<acervo>/`, vindo do perfil -- nao de um
   `output_dir` global trocado a mao a cada rodada.
4. O catalogo e gravado sob trava, porque o download paralelo escreve nele.
"""
import os
import subprocess
import threading
import time
import urllib.request

import yt_dlp

from . import ids as _ids

# --- PO Token (obrigatorio desde ago/2026) ---------------------------------
# Sem o token o yt-dlp cai no cliente android_vr e as URLs de midia dao 403.
# Ver docs/DOC-TECNICO.md ("Setup do PO Token").
POT_SERVER_URL = 'http://127.0.0.1:4416'
POT_SERVER_HOME = os.path.expanduser('~/bgutil-ytdlp-pot-provider/server')
JS_RUNTIME = 'node'

_TRAVA_CATALOGO = threading.Lock()
_FFMPEG_PRONTO = False


def garantir_ffmpeg():
    """Poe o ffmpeg do `static_ffmpeg` no PATH deste processo.

    Sem ffmpeg o pos-processamento para mp3 nao acontece e sobra o `.webm` --
    que e justamente o tipo de sobra que o T1.5 reclama. Nao se confia no
    ffmpeg do sistema: nesta maquina ele existe, na proxima pode nao existir.
    """
    global _FFMPEG_PRONTO
    if _FFMPEG_PRONTO:
        return True
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
        _FFMPEG_PRONTO = True
    except Exception as e:
        print(f'[ffmpeg] AVISO: static_ffmpeg falhou ({e}); '
              f'seguindo com o ffmpeg do sistema, se houver.')
    return _FFMPEG_PRONTO


def pot_no_ar(timeout=3):
    try:
        with urllib.request.urlopen(f'{POT_SERVER_URL}/ping', timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def garantir_pot(espera_segundos=60):
    """Sobe o servidor de PO Token se preciso. Devolve True se responde no fim."""
    if pot_no_ar():
        print(f'[POT] ja ativo em {POT_SERVER_URL}')
        return True

    main_js = os.path.join(POT_SERVER_HOME, 'build', 'main.js')
    if not os.path.exists(main_js):
        print(f'[POT] AVISO: servidor nao encontrado em {main_js}\n'
              f'[POT] os downloads vao falhar com HTTP 403. Ver docs/DOC-TECNICO.md')
        return False

    print(f'[POT] subindo: node {main_js}')
    subprocess.Popen([JS_RUNTIME, main_js], cwd=POT_SERVER_HOME,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    for _ in range(espera_segundos):
        if pot_no_ar():
            print('[POT] pronto.')
            return True
        time.sleep(1)
    print('[POT] AVISO: nao respondeu a tempo.')
    return False


# --- opcoes do yt-dlp -------------------------------------------------------

def pasta_do_acervo(perfil, raiz='output'):
    return os.path.join(raiz, perfil['acervo'])


def modelo_de_nome(perfil, raiz='output'):
    """`AAAA-MM-DD_Titulo_Sanitizado_[<id>].<ext>`.

    A data na frente ordena a pasta sozinha; o id no fim e a chave, e e o que
    permite a `varredura` reconstruir o catalogo a partir do disco.
    """
    return os.path.join(pasta_do_acervo(perfil, raiz),
                        '%(upload_date>%Y-%m-%d)s_%(title)s_[%(id)s].%(ext)s')


def _filtro(perfil, catalogo, pulados):
    """O match_filter do yt-dlp: devolve a razao da recusa, ou None para aceitar."""
    canais = [c.lower() for c in perfil.get('canais_permitidos', [])]
    janela = perfil.get('publicado_entre')
    dur_min = perfil.get('duracao_minima_minutos')
    dur_max = perfil.get('duracao_maxima_minutos')

    def filtro(info, *, incomplete=False):
        video_id = info.get('id')
        if video_id and catalogo.tem(video_id):
            reg = catalogo.registro(video_id)
            pulados.append({'id': video_id, 'titulo': reg.get('titulo') or info.get('title')})
            return f'ja esta na biblioteca (id {video_id})'

        if janela:
            data = info.get('upload_date')  # AAAAMMDD
            if data:
                dia = f'{data[:4]}-{data[4:6]}-{data[6:8]}'
                if dia < janela[0]:
                    return f'publicado em {dia}, antes de {janela[0]}'
                if dia > janela[1]:
                    return f'publicado em {dia}, depois de {janela[1]}'

        if canais:
            canal = info.get('channel') or info.get('uploader') or ''
            # Canal vazio e a fase de busca, onde a informacao ainda nao veio.
            if canal and not any(c in canal.lower() for c in canais):
                return f'canal "{canal}" fora dos permitidos'

        segundos = info.get('duration')
        if segundos:
            if dur_min and segundos < dur_min * 60:
                return f'dura {int(segundos)//60}min, menos que {dur_min}min'
            if dur_max and segundos > dur_max * 60:
                return f'dura {int(segundos)//60}min, mais que {dur_max}min'
        return None

    return filtro


def opcoes(perfil, catalogo, pulados, raiz='output', silencioso=False):
    opts = {
        'outtmpl': modelo_de_nome(perfil, raiz),
        'noplaylist': True,
        'restrictfilenames': True,
        'quiet': silencioso,
        'no_warnings': silencioso,
        'match_filter': _filtro(perfil, catalogo, pulados),
        # Sem runtime JS o YouTube nao entrega os formatos do cliente web.
        'js_runtimes': {JS_RUNTIME: {}},
        # O titulo vem no idioma pedido; fixamos pt para o nome do arquivo nao
        # mudar de lingua conforme o humor do YouTube. O id nao muda nunca.
        'extractor_args': {'youtube': {'lang': ['pt']}},
    }
    if perfil.get('formato', 'audio') == 'audio':
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        opts['format'] = 'bestvideo*+bestaudio/best'
        opts['merge_output_format'] = 'mp4'
    return opts


# --- o download -------------------------------------------------------------

def _anotar(catalogo, info, perfil, raiz):
    """Grava no catalogo o que acabou de descer. Sob trava: ha paralelismo."""
    video_id = info.get('id')
    if not video_id:
        return None
    baixados = info.get('requested_downloads') or []
    arquivo = baixados[0].get('filepath') if baixados else None
    if arquivo:
        try:
            arquivo = os.path.relpath(arquivo, os.getcwd())
        except ValueError:
            pass  # outro drive no Windows; fica o caminho absoluto
    data = info.get('upload_date')
    publicado = f'{data[:4]}-{data[4:6]}-{data[6:8]}' if data else None
    with _TRAVA_CATALOGO:
        reg = catalogo.anotar(
            video_id,
            titulo=info.get('title'),
            canal=info.get('channel') or info.get('uploader'),
            publicado=publicado,
            acervo=perfil['acervo'],
            arquivo=arquivo,
            formato=perfil.get('formato', 'audio'),
            origem='download',
        )
        catalogo.gravar()
    return reg


def baixar_alvo(alvo, perfil, catalogo, raiz='output', silencioso=False):
    """Baixa um alvo -- URL direta ou termo de busca.

    Devolve um dicionario de desfecho, com `estado` em
    `baixado`, `ja-temos`, `recusado` ou `erro`.
    """
    video_id = _ids.da_url(alvo)
    if video_id:
        if catalogo.tem(video_id):
            reg = catalogo.registro(video_id)
            return {'estado': 'ja-temos', 'id': video_id, 'alvo': alvo,
                    'titulo': reg.get('titulo'), 'arquivos': reg.get('arquivos', [])}
        pedido = _ids.url_canonica(video_id)
    else:
        pedido = f"ytsearch{perfil.get('resultados_por_busca', 10)}:{alvo}"

    garantir_ffmpeg()
    pulados = []
    opts = opcoes(perfil, catalogo, pulados, raiz, silencioso)
    if not video_id:
        # Numa busca queremos o primeiro resultado que passe nos filtros, nao os
        # dez. `max_downloads` para a varredura assim que um desce.
        opts['max_downloads'] = 1

    os.makedirs(pasta_do_acervo(perfil, raiz), exist_ok=True)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(pedido, download=True)
    except yt_dlp.utils.MaxDownloadsReached:
        return {'estado': 'baixado', 'alvo': alvo,
                'aviso': 'limite de 1 por busca atingido; ver catalogo'}
    except Exception as e:
        return {'estado': 'erro', 'alvo': alvo, 'erro': str(e)}

    if not info:
        return {'estado': 'recusado', 'alvo': alvo,
                'porque': pulados[0] if pulados else 'nenhum resultado passou nos filtros'}

    entradas = info.get('entries') if info.get('_type') == 'playlist' else [info]
    registrados = []
    for entrada in (entradas or []):
        if not entrada:
            continue
        reg = _anotar(catalogo, entrada, perfil, raiz)
        if reg:
            registrados.append(reg)

    if not registrados:
        return {'estado': 'recusado', 'alvo': alvo,
                'porque': pulados[0] if pulados else 'nada foi baixado'}
    return {'estado': 'baixado', 'alvo': alvo, 'registros': registrados}


def baixar_perfil(perfil, catalogo, raiz='output', paralelos=1, silencioso=False):
    """Roda todos os alvos de um perfil. `paralelos=1` e sequencial."""
    import concurrent.futures

    garantir_pot()
    alvos = perfil.get('alvos', [])
    if not alvos:
        print(f'[perfil {perfil["acervo"]}] nenhum alvo em "alvos".')
        return []

    if paralelos <= 1:
        return [baixar_alvo(a, perfil, catalogo, raiz, silencioso) for a in alvos]

    desfechos = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=paralelos) as pool:
        futuros = {pool.submit(baixar_alvo, a, perfil, catalogo, raiz, silencioso): a
                   for a in alvos}
        for futuro in concurrent.futures.as_completed(futuros):
            try:
                desfechos.append(futuro.result())
            except Exception as e:
                desfechos.append({'estado': 'erro', 'alvo': futuros[futuro], 'erro': str(e)})
    return desfechos
