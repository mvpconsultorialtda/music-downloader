---
tipo: documentacao
criado: 2026-04-07
atualizado: 2026-09-22
tags: [tech, music_downloader]
temas: [tech/music_downloader]
modo: tech
---

# Music Downloader

> **Aviso, 2026-09-22.** A reformulacao do ticket `0022-biblioteca-do-youtube`
> trocou a camada de uso: o baixador agora e `python -m biblioteca`, a instrucao
> mora em `perfis/<acervo>.json` e a memoria e o `catalogo.json`, chaveado pelo
> id do video. **Como se usa hoje esta no [`README.md`](../README.md).**
>
> As secoes abaixo que falam de `download_music.py`, `config.json` e `input/*.txt`
> descrevem o baixador anterior, que continua inteiro em [`legado/`](../legado/LEIA.md)
> e continua executavel. A secao **Setup do PO Token** vale para os dois e e a
> unica daqui de que a camada nova ainda depende.

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

## Descobrir o que ainda NAO foi baixado

`scripts/find_auvp_novos.py` cruza o catalogo do canal AUVP Capital com o que
ja existe (`history.json` + os nomes dos MP3 em `output/`) e imprime so o que
falta.

```bash
python scripts/find_auvp_novos.py            # usa o cache do canal
python scripts/find_auvp_novos.py --refresh  # rebusca a lista no YouTube
```

Duas armadilhas que o script ja trata, e que fazem video ja baixado reaparecer
como novo se voce escrever a comparacao na mao:

- **Titulos traduzidos.** Sem `extractor_args={"youtube": {"lang": ["pt"]}}` o
  YouTube devolve os titulos auto-traduzidos para ingles ("What happened to
  Shein?"), que nunca casam com os arquivos em portugues no disco. O codigo de
  idioma e `pt` — `pt-BR` e recusado pelo extractor.
- **Acentos.** A normalizacao precisa passar por `unicodedata.normalize("NFKD")`
  antes de jogar fora o que nao e `[a-z0-9]`. Sem isso "está" vira "est" e
  "esta" vira "esta", e o par nao casa. Foi exatamente o que escondeu o
  "MERCADO LIVRE virando um BANCO" na primeira rodada.

A dedup por `id` e a confiavel; a por titulo so existe porque os arquivos
baixados antes do `progress_hook` entraram no historico sem ID (`source:
disk_scan`).

## Aumentar o volume dos MP3

`scripts/boost_volume.py` aplica +25% de ganho (1.25x = +1.94 dB) em todos os
MP3 de `output/`, movendo os originais para `output_backup_pre_volume/`
preservando a arvore de pastas.

```bash
python scripts/boost_volume.py
```

**Por que tem um limiter no meio.** Os arquivos do canal chegam com pico em
torno de -0.4 dBFS e media em -18 dB: o que soa baixo e a media, nao o pico.
Um `volume=1.25` puro estoura o teto e distorce. Por isso a cadeia e

```
volume=1.25,alimiter=level_in=1:level_out=1:limit=0.98:attack=5:release=50
```

O corpo do audio sobe os 25% pedidos e so os picos curtos encostam no limiter.
Se o que voce quer e volume *consistente* entre arquivos (e nao +25% sobre cada
um), troque a cadeia por `loudnorm=I=-16:TP=-1.5:LRA=11`.

O script e resumivel: arquivo que ja tem copia em `output_backup_pre_volume/`
e pulado, entao da para interromper e rodar de novo. O bitrate de saida
acompanha o da origem.

## Roadmap

- Suporte a playlists
- Download de video (nao apenas audio)
- Interface CLI interativa com selecao de resultados
- Integracao com Spotify para baixar a partir de playlists
