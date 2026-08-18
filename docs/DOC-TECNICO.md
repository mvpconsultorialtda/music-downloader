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

- `yt-dlp` (nightly) — downloader YouTube
- `yt-dlp-ejs` + Node.js >= 20 — resolve os desafios JS do YouTube
- `bgutil-ytdlp-pot-provider` + servidor Node — gera o PO Token
- `static_ffmpeg` — FFmpeg bundled (sem instalacao manual)
- Acesso a internet para buscas no YouTube

## Setup do PO Token (obrigatorio desde ago/2026)

### O sintoma

Todo download morre em `HTTP Error 403: Forbidden`, mesmo com a extracao de
metadados funcionando normalmente. No log verboso aparece:

```
[pot] PO Token Providers: none
Detected experiment to bind GVS PO Token to video ID
YouTube is forcing SABR streaming for this client
[youtube] <id>: Downloading android vr player API JSON
```

### A causa

O YouTube passou a exigir um **PO Token** (Proof of Origin) nos clientes web.
Sem um provider de token o yt-dlp nao consegue formatos pelo cliente web e cai
no `android_vr`, cujas URLs de midia o CDN recusa com 403. Videos antigos (pre
2010) escapam da exigencia — por isso um teste com video velho da falso
negativo. Nada disso e culpa do repo: rodou normal ate 02/08/2026 e parou
sozinho quando o YouTube ligou o experimento.

### O setup

```bash
pip install -r requirements.txt   # ja traz yt-dlp nightly + o plugin

# servidor gerador do token (uma vez)
git clone --depth 1 --branch 1.3.1 \
  https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
  ~/bgutil-ytdlp-pot-provider
cd ~/bgutil-ytdlp-pot-provider/server && npm install && npx tsc
```

O `download_music.py` sobe o servidor sozinho (`ensure_pot_server()`) e checa
o `/ping` em `127.0.0.1:4416`. Para subir na mao:

```bash
node ~/bgutil-ytdlp-pot-provider/server/build/main.js
```

### Cuidados

- **Use o yt-dlp nightly.** A versao estavel nao acompanha os experimentos que
  o YouTube liga sem aviso — a estavel de fev/2026 falhava, a nightly resolveu.
- **A versao do servidor tem que casar com a do plugin pip** (hoje 1.3.1).
- **Modo script nao funciona bem no Windows:** o cold start do
  `generate_once.js` leva ~44s e estoura o timeout de 15s do plugin. Por isso
  o padrao aqui e o servidor HTTP, que fica quente entre chamadas.
- `js_runtimes` na API Python e **dict** (`{'node': {}}`), nao a lista do CLI.

### Verificar integridade apos baixar

O MP3 pode sair truncado se o processo for interrompido durante a conversao —
e o arquivo parcial ainda entra no `history.json`, mascarando a falha. Compare
a duracao real com a do metadado:

```bash
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 arquivo.mp3
```

Divergencia > 0.6 min = truncado: apague o arquivo, remova a entrada do
`history.json` e baixe de novo.

## Roadmap

- Suporte a playlists
- Download de video (nao apenas audio)
- Interface CLI interativa com selecao de resultados
- Integracao com Spotify para baixar a partir de playlists
