---
tipo: documentacao
criado: 2026-04-07
atualizado: 2026-04-07
tags: [tech, music_downloader]
temas: [tech/music_downloader]
modo: tech
---

# Music Downloader

## Visao Geral

Script Python para download de audio do YouTube via busca por texto. Le queries de arquivos `.txt` na pasta `input/`, baixa os audios encontrados para `output/` em formato MP3, com filtro de data (apenas 2025 por default) e historico de downloads para evitar duplicatas.

## Modelo de Negocio

Ferramenta interna / utilitario. Provavelmente usada para montar playlists ou bancos de musica para uso em projetos de audio/podcast/conteudo da MVP.

## Stack Tecnologica

| Camada | Tecnologia | Versao |
|--------|-----------|--------|
| Linguagem | Python | 3.x |
| Download YouTube | yt-dlp | — |
| FFmpeg (bundled) | static_ffmpeg | — |

## Arquitetura

```
input/*.txt         — arquivos com uma query por linha
    │
    download_music.py
    │   ├── carrega config.json
    │   ├── le queries dos .txt
    │   ├── filtro de data (2025 por default)
    │   └── yt-dlp search → download MP3
    │
output/             — arquivos MP3 baixados
history.json        — registro de downloads anteriores (evita duplicatas)
```

Tambem inclui `split_audio.py` para divisao de arquivos de audio.

## Como Rodar Localmente

```bash
pip install -r requirements.txt

# Criar pasta input/ e adicionar arquivos .txt com queries
mkdir input
echo "Nome da musica - Artista" > input/minhas_musicas.txt

python download_music.py
```

## Estrutura de Pastas

```
music_downloader/
├── download_music.py      # Script principal de download
├── split_audio.py         # Script para dividir arquivos de audio
├── config.json            # Configuracao (filtros, opcoes yt-dlp)
├── history.json           # Historico de downloads
├── requirements.txt       # yt-dlp, static_ffmpeg
├── verification_log.txt   # Log de verificacoes
├── input/                 # Arquivos .txt com queries de busca
└── output/                # Arquivos MP3 baixados
```

## APIs e Endpoints

Sem API — ferramenta de linha de comando.

## Configuracao (config.json)

- `filter_after_2025` (bool): se `true`, baixa apenas videos de 2025

## Deploy

Execucao local apenas. Sem deploy.

## Dependencias Externas

- `yt-dlp` — downloader YouTube
- `static_ffmpeg` — FFmpeg bundled (sem instalacao manual)
- Acesso a internet para buscas no YouTube

## Roadmap

- Suporte a playlists
- Download de video (nao apenas audio)
- Interface CLI interativa com selecao de resultados
- Integracao com Spotify para baixar a partir de playlists
