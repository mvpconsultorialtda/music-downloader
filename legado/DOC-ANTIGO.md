# O baixador anterior, documentado como ele era

Isto saiu de `docs/DOC-TECNICO.md` em 2026-09-23. Nao foi corrigido nem atualizado —
e o registro de como a ferramenta funcionava antes da reformulacao do ticket
`0022-biblioteca-do-youtube`, e vale para ler o codigo que esta nesta pasta.

**Nada aqui descreve o uso atual.** Para isso, [`README.md`](../README.md).

> O que continua valendo, e por isso ficou em `docs/`: o setup do PO Token e a
> verificacao de integridade do mp3 depois de baixar.

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


## Descobrir o que ainda NAO foi baixado

`legado/scripts/find_auvp_novos.py` cruza o catalogo do canal AUVP Capital com o que
ja existe (`history.json` + os nomes dos MP3 em `output/`) e imprime so o que
falta.

```bash
python legado/scripts/find_auvp_novos.py            # usa o cache do canal
python legado/scripts/find_auvp_novos.py --refresh  # rebusca a lista no YouTube
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

`legado/scripts/boost_volume.py` aplica +25% de ganho (1.25x = +1.94 dB) em todos os
MP3 de `output/`, movendo os originais para `output_backup_pre_volume/`
preservando a arvore de pastas.

```bash
python legado/scripts/boost_volume.py
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


---

## O que desta pagina virou codigo na camada nova

Duas armadilhas documentadas aqui, na secao "Descobrir o que ainda NAO foi baixado",
sobreviveram a reformulacao porque sao verdades sobre o YouTube, nao sobre o script:

- **Titulos traduzidos.** `extractor_args={"youtube": {"lang": ["pt"]}}`, e o codigo
  e `pt` — `pt-BR` o extractor recusa. Hoje isso esta em
  `biblioteca/baixador.py:opcoes()`, e so para o **nome do arquivo** nao trocar de
  lingua: a identidade e o id, nunca o titulo.
- **Acentos.** `unicodedata.normalize("NFKD")` antes de descartar o que nao e
  `[a-z0-9]`, senao "esta" com acento vira "est" e nao casa com o nome de arquivo
  sanitizado. Hoje em `biblioteca/varredura.py:assinatura()` — e ela **so** serve para
  recuperar o id de material antigo, nunca para decidir se um video ja desceu.

A primeira versao da camada nova errou a segunda, e este arquivo foi onde o erro
apareceu. Documento velho que ninguem le e defeito que volta.
